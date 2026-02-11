import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { StaticWebsite } from '@aws-solutions-constructs/aws-s3-cloudfront';
// import * as sqs from 'aws-cdk-lib/aws-sqs';

export class Cdk2Stack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here, good luck 🚀!! 

    // Construct L1 (NIVEL BASICO)
    // new cdk.aws_s3.CfnBucket(this, "MyFirstBucket", {
    //   bucketName: "my-first-bucket-" +  cdk.Aws.ACCOUNT_ID + '-' + cdk.Aws.REGION
    // });

    // Construct L2 (NIVEL  MEDIO-ALTO)
    const actualDate = new Date();

    const bucketL2 =  new cdk.aws_s3.Bucket(this, "MySecondBucket", {  
      bucketName: "my-second-bucket-" + cdk.Aws.ACCOUNT_ID + '-' + cdk.Aws.REGION + '-' + Date.now()
    })

      

    // Subimos objetos al Bucket
    new cdk.aws_s3_deployment.BucketDeployment(this, "DeployWithInvalidation", {
      sources: [cdk.aws_s3_deployment.Source.asset("./resources")],
      destinationBucket: bucketL2
    })

    // Construct L3 (NIVEL ALTO)

    

const website = new StaticWebsite(this, 'MyWebsite', {
  websiteIndexDocument: 'index.html',
  websiteErrorDocument: 'error.html'
});

  }
}
