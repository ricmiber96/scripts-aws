#!/usr/bin/env python3
import boto3
import time

def get_amazon_linux_ami(ec2_client):
    """Obtiene la AMI más reciente de Amazon Linux 2023"""
    response = ec2_client.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['al2023-ami-*-x86_64']},
            {'Name': 'owner-id', 'Values': ['137112412989']},  # Amazon
            {'Name': 'state', 'Values': ['available']}
        ]
    )
    images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
    return images[0]['ImageId']

def create_juice_shop_infrastructure():
    """Crea toda la infraestructura para Juice Shop con WAF"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    elbv2 = boto3.client('elbv2', region_name='us-east-1')
    wafv2 = boto3.client('wafv2', region_name='us-east-1')
    
    print("=== Creando infraestructura Juice Shop ===")
    
    # Obtener AMI de Amazon Linux 2023
    ami_id = get_amazon_linux_ami(ec2)
    print(f"AMI Amazon Linux 2023: {ami_id}")
    
    # 1. Crear VPC
    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    ec2.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': 'JuiceShop-VPC'}])
    print(f"VPC creada: {vpc_id}")
    
    # Habilitar DNS
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})
    
    # 2. Crear Internet Gateway
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    ec2.create_tags(Resources=[igw_id], Tags=[{'Key': 'Name', 'Value': 'JuiceShop-IGW'}])
    print(f"Internet Gateway: {igw_id}")
    
    # 3. Crear dos subredes públicas en diferentes AZ
    azs = ec2.describe_availability_zones(Filters=[{'Name': 'state', 'Values': ['available']}])
    az1 = azs['AvailabilityZones'][0]['ZoneName']
    az2 = azs['AvailabilityZones'][1]['ZoneName']
    
    subnet1_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.1.0/24', AvailabilityZone=az1)
    subnet1_id = subnet1_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet1_id], Tags=[{'Key': 'Name', 'Value': 'JuiceShop-Subnet-1'}])
    
    subnet2_response = ec2.create_subnet(VpcId=vpc_id, CidrBlock='10.0.2.0/24', AvailabilityZone=az2)
    subnet2_id = subnet2_response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet2_id], Tags=[{'Key': 'Name', 'Value': 'JuiceShop-Subnet-2'}])
    
    # Habilitar IP pública automática
    ec2.modify_subnet_attribute(SubnetId=subnet1_id, MapPublicIpOnLaunch={'Value': True})
    ec2.modify_subnet_attribute(SubnetId=subnet2_id, MapPublicIpOnLaunch={'Value': True})
    
    print(f"Subredes creadas: {subnet1_id} ({az1}), {subnet2_id} ({az2})")
    
    # 4. Configurar tabla de rutas
    route_tables = ec2.describe_route_tables(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
    main_rt_id = route_tables['RouteTables'][0]['RouteTableId']
    ec2.create_route(RouteTableId=main_rt_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw_id)
    
    # 5. Crear Security Group
    sg_response = ec2.create_security_group(
        GroupName='JuiceShop-SG',
        Description='Security group for Juice Shop',
        VpcId=vpc_id
    )
    sg_id = sg_response['GroupId']
    ec2.create_tags(Resources=[sg_id], Tags=[{'Key': 'Name', 'Value': 'JuiceShop-SG'}])
    
    # Reglas de seguridad
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    print(f"Security Group creado: {sg_id}")
    
    # 6. User Data para instalar Docker y Juice Shop
    user_data = """#!/bin/bash
yum update -y
yum install -y docker
service docker start
systemctl enable docker.service
docker pull bkimminich/juice-shop
docker run -d -p 80:3000 bkimminich/juice-shop"""
    
    # 7. Crear instancias EC2
    instance1_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SubnetId=subnet1_id,
        SecurityGroupIds=[sg_id],
        UserData=user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'JuiceShop-Instance-1'}]
        }]
    )
    instance1_id = instance1_response['Instances'][0]['InstanceId']
    
    instance2_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SubnetId=subnet2_id,
        SecurityGroupIds=[sg_id],
        UserData=user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'JuiceShop-Instance-2'}]
        }]
    )
    instance2_id = instance2_response['Instances'][0]['InstanceId']
    
    print(f"Instancias creadas: {instance1_id}, {instance2_id}")
    
    # Esperar a que las instancias estén en estado running
    print("Esperando a que las instancias estén ejecutándose...")
    ec2.get_waiter('instance_running').wait(InstanceIds=[instance1_id, instance2_id])
    print("Instancias ejecutándose")
    
    # 8. Crear Target Group
    tg_response = elbv2.create_target_group(
        Name='JuiceShop-TG',
        Protocol='HTTP',
        Port=80,
        VpcId=vpc_id,
        TargetType='instance'
    )
    tg_arn = tg_response['TargetGroups'][0]['TargetGroupArn']
    print(f"Target Group creado: {tg_arn}")
    
    # Registrar instancias en Target Group
    elbv2.register_targets(
        TargetGroupArn=tg_arn,
        Targets=[
            {'Id': instance1_id},
            {'Id': instance2_id}
        ]
    )
    
    # 9. Crear Application Load Balancer
    alb_response = elbv2.create_load_balancer(
        Name='JuiceShop-ALB',
        Subnets=[subnet1_id, subnet2_id],
        SecurityGroups=[sg_id],
        Scheme='internet-facing',
        Type='application'
    )
    alb_arn = alb_response['LoadBalancers'][0]['LoadBalancerArn']
    alb_dns = alb_response['LoadBalancers'][0]['DNSName']
    print(f"ALB creado: {alb_arn}")
    print(f"ALB DNS: {alb_dns}")
    
    # Esperar a que el ALB esté disponible
    print("Esperando que el ALB esté disponible...")
    elbv2.get_waiter('load_balancer_available').wait(LoadBalancerArns=[alb_arn])
    
    # 10. Crear Listener
    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[{
            'Type': 'forward',
            'TargetGroupArn': tg_arn
        }]
    )
    
    # 11. Crear Web ACL
    web_acl_response = wafv2.create_web_acl(
        Scope='REGIONAL',
        DefaultAction={'Allow': {}},
        Rules=[
            {
                'Name': 'AWSManagedRulesCommonRuleSet',
                'Priority': 1,
                'OverrideAction': {'None': {}},
                'Statement': {
                    'ManagedRuleGroupStatement': {
                        'VendorName': 'AWS',
                        'Name': 'AWSManagedRulesCommonRuleSet'
                    }
                },
                'VisibilityConfig': {
                    'SampledRequestsEnabled': True,
                    'CloudWatchMetricsEnabled': True,
                    'MetricName': 'CommonRuleSetMetric'
                }
            },
            {
                'Name': 'AWSManagedRulesSQLiRuleSet',
                'Priority': 2,
                'OverrideAction': {'None': {}},
                'Statement': {
                    'ManagedRuleGroupStatement': {
                        'VendorName': 'AWS',
                        'Name': 'AWSManagedRulesSQLiRuleSet'
                    }
                },
                'VisibilityConfig': {
                    'SampledRequestsEnabled': True,
                    'CloudWatchMetricsEnabled': True,
                    'MetricName': 'SQLiRuleSetMetric'
                }
            },
            {
                'Name': 'RateLimitRule',
                'Priority': 3,
                'Action': {'Block': {}},
                'Statement': {
                    'RateBasedStatement': {
                        'Limit': 100,
                        'AggregateKeyType': 'IP'
                    }
                },
                'VisibilityConfig': {
                    'SampledRequestsEnabled': True,
                    'CloudWatchMetricsEnabled': True,
                    'MetricName': 'RateLimitMetric'
                }
            }
        ],
        VisibilityConfig={
            'SampledRequestsEnabled': True,
            'CloudWatchMetricsEnabled': True,
            'MetricName': 'JuiceShopWebACL'
        },
        Name='JuiceShop-WebACL'
    )
    web_acl_arn = web_acl_response['Summary']['ARN']
    print(f"Web ACL creada: {web_acl_arn}")
    
    # 12. Asociar Web ACL con ALB
    wafv2.associate_web_acl(
        WebACLArn=web_acl_arn,
        ResourceArn=alb_arn
    )
    
    print("\n=== RESUMEN ===")
    print(f"VPC: {vpc_id}")
    print(f"Subredes: {subnet1_id}, {subnet2_id}")
    print(f"Instancias: {instance1_id}, {instance2_id}")
    print(f"ALB: {alb_dns}")
    print(f"Web ACL: {web_acl_arn}")
    print("\n✅ Infraestructura Juice Shop creada exitosamente!")
    print(f"🌐 Accede a la aplicación en: http://{alb_dns}")

def main():
    try:
        create_juice_shop_infrastructure()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()