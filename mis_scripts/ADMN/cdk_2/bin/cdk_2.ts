#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { Cdk2Stack } from '../lib/cdk_2-stack';

const app = new cdk.App();
new Cdk2Stack(app, 'Cdk2Stack', {
  
  env: { account: process.env.ACCOUNT_ID, region: process.env.REGION },

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-east-1' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});
