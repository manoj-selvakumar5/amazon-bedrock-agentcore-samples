import * as cdk from 'aws-cdk-lib';
import { CfnOutput, Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as appconfig from 'aws-cdk-lib/aws-appconfig';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambda_ from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface InfraConstructProps {
  /** Destroy tables, bucket, queues and keys with the stack (a sample, not production). */
  destroyOnDelete?: boolean;
}

/** Tool Lambda for each Gateway target, keyed by the target name in agentcore.json. */
const TOOL_TARGETS: { target: string; dir: string; functionName: string }[] = [
  { target: 'get-user-profile', dir: 'get_user_profile', functionName: 'ReceiptsAgent-GetUserProfile' },
  { target: 'get-recent-expenses', dir: 'get_recent_expenses', functionName: 'ReceiptsAgent-GetRecentExpenses' },
  { target: 'lookup-merchant', dir: 'lookup_merchant', functionName: 'ReceiptsAgent-LookupMerchant' },
  { target: 'save-expense', dir: 'save_expense', functionName: 'ReceiptsAgent-SaveExpense' },
  { target: 'human-review', dir: 'human_review', functionName: 'ReceiptsAgent-HumanReview' },
];

/**
 * Model settings the agent reads live from AppConfig (docs/CONFIGURATION.md). Deploy a new
 * version to change the model or its inference parameters without redeploying the agent.
 * Optional keys: temperature, maxTokens, topP. A key left out keeps the model's default.
 */
const MODEL_SETTINGS = {
  modelId: 'global.anthropic.claude-opus-4-8',
};

/**
 * Supplementary AWS infrastructure for the receipts agent: everything the AgentCore
 * constructs do not create. Resource names are fixed because the scripts and live tests
 * look them up by name.
 */
export class InfraConstruct extends Construct {
  /** Real Lambda ARN per Gateway target name, used to patch the PLACEHOLDER_* targets. */
  public readonly lambdaArnMap: Record<string, string> = {};
  public readonly inbox: s3.Bucket;
  public readonly runBus: events.EventBus;
  public readonly identityKey: kms.Key;
  public readonly triggerFn: lambda_.Function;
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;
  public readonly cognitoDiscoveryUrl: string;
  public readonly cognitoTokenEndpoint: string;
  public readonly appConfigApplicationId: string;
  public readonly appConfigEnvironmentId: string;
  public readonly appConfigProfileId: string;

  constructor(scope: Construct, id: string, props: InfraConstructProps = {}) {
    super(scope, id);

    const stack = cdk.Stack.of(this);
    const removalPolicy = props.destroyOnDelete ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN;
    // The CLI runs synth from agentcore/cdk; the sample root is two levels up.
    const projectRoot = path.resolve(process.cwd(), '..', '..');
    const lambdaCode = (dir: string) => lambda_.Code.fromAsset(path.join(projectRoot, 'lambdas', dir));

    // ─── DynamoDB ──────────────────────────────────────────────────────────
    const usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: 'ReceiptsAgent-Users',
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy,
    });
    const expensesTable = new dynamodb.Table(this, 'ExpensesTable', {
      tableName: 'ReceiptsAgent-Expenses',
      partitionKey: { name: 'userId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'expenseId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy,
    });
    const merchantsTable = new dynamodb.Table(this, 'MerchantsTable', {
      tableName: 'ReceiptsAgent-Merchants',
      partitionKey: { name: 'merchantKey', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy,
    });
    // One fate row per receipt (ADR-0015); status-index answers "everything in review".
    const runsTable = new dynamodb.Table(this, 'ProcessingRunsTable', {
      tableName: 'ReceiptsAgent-ProcessingRuns',
      partitionKey: { name: 'receiptId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy,
    });
    runsTable.addGlobalSecondaryIndex({
      indexName: 'status-index',
      partitionKey: { name: 'status', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'processedAt', type: dynamodb.AttributeType.STRING },
    });

    // ─── S3 inbox (the front door) ─────────────────────────────────────────
    this.inbox = new s3.Bucket(this, 'InboxBucket', {
      bucketName: `receipts-inbox-${stack.account}-${stack.region}`,
      eventBridgeEnabled: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy,
      autoDeleteObjects: props.destroyOnDelete ?? false,
    });

    // ─── Queues ────────────────────────────────────────────────────────────
    const triggerDlq = new sqs.Queue(this, 'TriggerDLQ', {
      queueName: 'ReceiptsAgent-TriggerDLQ',
      retentionPeriod: Duration.days(14),
      enforceSSL: true,
      removalPolicy,
    });

    // ─── Identity key for the chat's signed tokens (ADR-0016) ──────────────
    this.identityKey = new kms.Key(this, 'IdentityKey', {
      description: 'HMAC key that signs and verifies chat identity tokens (ReceiptsAgent)',
      keySpec: kms.KeySpec.HMAC_256,
      keyUsage: kms.KeyUsage.GENERATE_VERIFY_MAC,
      removalPolicy,
    });

    // ─── Cognito: the agent's M2M identity to the Gateway (ADR-0004) ───────
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'ReceiptsAgent-Gateway',
      selfSignUpEnabled: false,
      removalPolicy,
    });
    const resourceServer = this.userPool.addResourceServer('ResourceServer', {
      identifier: 'agentcore',
      scopes: [{ scopeName: 'invoke', scopeDescription: 'Invoke the receipts Gateway' }],
    });
    const domain = this.userPool.addDomain('Domain', {
      cognitoDomain: { domainPrefix: `receipts-agent-${stack.account}` },
    });
    this.userPoolClient = this.userPool.addClient('Client', {
      userPoolClientName: 'ReceiptsAgent-M2M',
      generateSecret: true,
      oAuth: {
        flows: { clientCredentials: true },
        scopes: [cognito.OAuthScope.custom('agentcore/invoke')],
      },
    });
    this.userPoolClient.node.addDependency(resourceServer);
    this.cognitoDiscoveryUrl = `https://cognito-idp.${stack.region}.amazonaws.com/${this.userPool.userPoolId}/.well-known/openid-configuration`;
    this.cognitoTokenEndpoint = `https://${domain.domainName}.auth.${stack.region}.amazoncognito.com/oauth2/token`;

    // ─── Gateway tool Lambdas ──────────────────────────────────────────────
    const toolEnv: Record<string, string> = {
      USERS_TABLE: usersTable.tableName,
      EXPENSES_TABLE: expensesTable.tableName,
      MERCHANTS_TABLE: merchantsTable.tableName,
    };
    const tools: Record<string, lambda_.Function> = {};
    for (const tool of TOOL_TARGETS) {
      const fn = new lambda_.Function(this, `Tool-${tool.dir}`, {
        functionName: tool.functionName,
        runtime: lambda_.Runtime.PYTHON_3_12,
        handler: 'handler.handler',
        code: lambdaCode(tool.dir),
        timeout: Duration.seconds(30),
        memorySize: 256,
        environment: toolEnv,
      });
      tools[tool.dir] = fn;
      this.lambdaArnMap[tool.target] = fn.functionArn;
    }
    usersTable.grantReadData(tools.get_user_profile);
    expensesTable.grantReadData(tools.get_recent_expenses);
    merchantsTable.grantReadData(tools.lookup_merchant);
    expensesTable.grantReadWriteData(tools.save_expense);
    expensesTable.grantReadWriteData(tools.human_review);

    // ─── Front door: S3 "Object Created" -> trigger -> Runtime ─────────────
    this.triggerFn = new lambda_.Function(this, 'TriggerFn', {
      functionName: 'ReceiptsAgent-Trigger',
      runtime: lambda_.Runtime.PYTHON_3_12,
      handler: 'handler.handler',
      code: lambdaCode('trigger'),
      timeout: Duration.minutes(5),
      memorySize: 256,
      environment: { AGENTCORE_RUNTIME_ARN: 'PENDING', DEFAULT_USER_ID: 'user-001' },
    });
    this.inbox.grantRead(this.triggerFn);
    new events.Rule(this, 'InboxObjectCreatedRule', {
      ruleName: 'ReceiptsAgent-InboxObjectCreated',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: { bucket: { name: [this.inbox.bucketName] }, object: { key: [{ prefix: 'receipts/' }] } },
      },
      targets: [
        new targets.LambdaFunction(this.triggerFn, {
          deadLetterQueue: triggerDlq,
          retryAttempts: 2,
          maxEventAge: Duration.hours(2),
        }),
      ],
    });

    // ─── Run ledger: agent -> bus -> ledger writer; errors -> SNS ──────────
    this.runBus = new events.EventBus(this, 'RunBus', { eventBusName: 'ReceiptsAgent-RunLedger' });
    const ledgerFn = new lambda_.Function(this, 'LedgerWriterFn', {
      functionName: 'ReceiptsAgent-LedgerWriter',
      runtime: lambda_.Runtime.PYTHON_3_12,
      handler: 'handler.handler',
      code: lambdaCode('ledger_writer'),
      timeout: Duration.seconds(30),
      memorySize: 256,
      environment: { RUNS_TABLE: runsTable.tableName },
    });
    runsTable.grantReadWriteData(ledgerFn);
    new events.Rule(this, 'RunLedgerRule', {
      eventBus: this.runBus,
      eventPattern: { source: ['receipts.agent'], detailType: ['ReceiptProcessed'] },
      targets: [new targets.LambdaFunction(ledgerFn)],
    });
    const runErrors = new sns.Topic(this, 'RunErrorsTopic', { topicName: 'ReceiptsAgent-RunErrors' });
    new events.Rule(this, 'RunErrorRule', {
      eventBus: this.runBus,
      eventPattern: { source: ['receipts.agent'], detailType: ['ReceiptProcessed'], detail: { status: ['error'] } },
      targets: [new targets.SnsTopic(runErrors)],
    });

    // ─── Model settings: AppConfig, read live by the agent (ADR-0008) ──────
    const settingsApp = new appconfig.CfnApplication(this, 'ModelSettingsApp', { name: 'ReceiptsAgent-ModelSettings' });
    const settingsEnv = new appconfig.CfnEnvironment(this, 'ModelSettingsEnv', {
      applicationId: settingsApp.ref,
      name: 'dev',
    });
    const settingsProfile = new appconfig.CfnConfigurationProfile(this, 'ModelSettingsProfile', {
      applicationId: settingsApp.ref,
      name: 'model-settings',
      locationUri: 'hosted',
      type: 'AWS.Freeform',
    });
    const settingsVersion = new appconfig.CfnHostedConfigurationVersion(this, 'ModelSettingsVersion', {
      applicationId: settingsApp.ref,
      configurationProfileId: settingsProfile.ref,
      content: JSON.stringify(MODEL_SETTINGS),
      contentType: 'application/json',
    });
    const settingsStrategy = new appconfig.CfnDeploymentStrategy(this, 'ModelSettingsStrategy', {
      name: 'ReceiptsAgent-AllAtOnce',
      deploymentDurationInMinutes: 0,
      growthFactor: 100,
      finalBakeTimeInMinutes: 0,
      replicateTo: 'NONE',
    });
    new appconfig.CfnDeployment(this, 'ModelSettingsDeployment', {
      applicationId: settingsApp.ref,
      environmentId: settingsEnv.ref,
      configurationProfileId: settingsProfile.ref,
      configurationVersion: settingsVersion.ref,
      deploymentStrategyId: settingsStrategy.ref,
    });
    this.appConfigApplicationId = settingsApp.ref;
    this.appConfigEnvironmentId = settingsEnv.ref;
    this.appConfigProfileId = settingsProfile.ref;

    // ─── Outputs read by scripts and live tests (matched by prefix) ────────
    new CfnOutput(this, 'UserPoolId', { value: this.userPool.userPoolId });
    new CfnOutput(this, 'UserPoolClientId', { value: this.userPoolClient.userPoolClientId });
    new CfnOutput(this, 'IdentityKeyId', { value: this.identityKey.keyId });
    new CfnOutput(this, 'InboxBucketName', { value: this.inbox.bucketName });
  }
}
