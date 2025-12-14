#!/usr/bin/env python3
import boto3
import json

def create_monitoring_infrastructure():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Crear VPC
    vpc_response = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc_id = vpc_response['Vpc']['VpcId']
    
    # Habilitar DNS hostname
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    
    # Crear Internet Gateway
    igw_response = ec2.create_internet_gateway()
    igw_id = igw_response['InternetGateway']['InternetGatewayId']
    
    # Asociar IGW a VPC
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    
    # Crear subred pública
    subnet_response = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='10.0.1.0/24',
        AvailabilityZone='us-east-1a'
    )
    subnet_id = subnet_response['Subnet']['SubnetId']
    
    # Habilitar IP pública automática
    ec2.modify_subnet_attribute(
        SubnetId=subnet_id,
        MapPublicIpOnLaunch={'Value': True}
    )
    
    # Crear tabla de rutas
    route_table_response = ec2.create_route_table(VpcId=vpc_id)
    route_table_id = route_table_response['RouteTable']['RouteTableId']
    
    # Agregar ruta al IGW
    ec2.create_route(
        RouteTableId=route_table_id,
        DestinationCidrBlock='0.0.0.0/0',
        GatewayId=igw_id
    )
    
    # Asociar tabla de rutas con subred
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
    
    # Crear Security Group
    sg_response = ec2.create_security_group(
        GroupName='monitoring-sg',
        Description='Security group for monitoring infrastructure',
        VpcId=vpc_id
    )
    sg_id = sg_response['GroupId']
    
    # Reglas de seguridad
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 9090,
                'ToPort': 9090,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 9100,
                'ToPort': 9100,
                'IpRanges': [{'CidrIp': '10.0.0.0/16'}]
            }
        ]
    )
    
    # Obtener AMI de Ubuntu
    images = ec2.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'owner-alias', 'Values': ['amazon']}
        ],
        Owners=['099720109477']
    )
    ami_id = sorted(images['Images'], key=lambda x: x['CreationDate'])[-1]['ImageId']
    
    # User data para ec2_a (node exporter)
    ec2_a_userdata = """#!/bin/bash
apt update
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.6.1.linux-amd64.tar.gz
sudo cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/
sudo useradd --no-create-home --shell /bin/false node_exporter
sudo chown node_exporter:node_exporter /usr/local/bin/node_exporter
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
"""
    
    # User data para prometheus
    prometheus_userdata = """#!/bin/bash
apt update
apt install -y wget
wget https://github.com/prometheus/prometheus/releases/download/v2.47.0/prometheus-2.47.0.linux-amd64.tar.gz
tar xvfz prometheus-2.47.0.linux-amd64.tar.gz
sudo cp prometheus-2.47.0.linux-amd64/prometheus /usr/local/bin/
sudo cp prometheus-2.47.0.linux-amd64/promtool /usr/local/bin/
sudo mkdir /etc/prometheus /var/lib/prometheus
sudo cp -r prometheus-2.47.0.linux-amd64/consoles /etc/prometheus
sudo cp -r prometheus-2.47.0.linux-amd64/console_libraries /etc/prometheus
sudo useradd --no-create-home --shell /bin/false prometheus
sudo chown prometheus:prometheus /usr/local/bin/prometheus /usr/local/bin/promtool
sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node'
    static_configs:
      - targets: ['EC2_A_IP:9100']
EOF
sudo tee /etc/systemd/system/prometheus.service > /dev/null <<EOF
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus --config.file /etc/prometheus/prometheus.yml --storage.tsdb.path /var/lib/prometheus/ --web.console.templates=/etc/prometheus/consoles --web.console.libraries=/etc/prometheus/console_libraries

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
"""
    
    # Crear instancia ec2_a
    ec2_a_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[sg_id],
        SubnetId=subnet_id,
        UserData=ec2_a_userdata,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': 'ec2_a'}]
            }
        ]
    )
    
    # Crear instancia prometheus
    prometheus_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[sg_id],
        SubnetId=subnet_id,
        UserData=prometheus_userdata,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': 'prometheus'}]
            }
        ]
    )
    
    # Obtener IPs
    ec2_a_id = ec2_a_response['Instances'][0]['InstanceId']
    prometheus_id = prometheus_response['Instances'][0]['InstanceId']
    
    # Esperar a que las instancias estén corriendo
    print("Esperando a que las instancias estén corriendo...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[ec2_a_id, prometheus_id])
    
    # Obtener IPs públicas
    instances = ec2.describe_instances(InstanceIds=[ec2_a_id, prometheus_id])
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unknown')
            public_ip = instance.get('PublicIpAddress', 'N/A')
            private_ip = instance.get('PrivateIpAddress', 'N/A')
            print(f"{name}: Public IP: {public_ip}, Private IP: {private_ip}")
    
    print(f"\nInfraestructura creada exitosamente!")
    print(f"VPC ID: {vpc_id}")
    print(f"Subnet ID: {subnet_id}")
    print(f"Security Group ID: {sg_id}")
    print(f"Prometheus será accesible en: http://{public_ip}:9090")

if __name__ == "__main__":
    create_monitoring_infrastructure()