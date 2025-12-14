#!/usr/bin/env python3
import boto3
import sys

def add_grafana_instance(vpc_id, subnet_id):
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Crear Security Group para Grafana
    grafana_sg_response = ec2.create_security_group(
        GroupName='grafana-sg',
        Description='Security group for Grafana instance',
        VpcId=vpc_id
    )
    grafana_sg_id = grafana_sg_response['GroupId']
    
    # Reglas de seguridad para Grafana
    ec2.authorize_security_group_ingress(
        GroupId=grafana_sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 3000,
                'ToPort': 3000,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )
    
    # Obtener IP de Prometheus
    prometheus_instances = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['prometheus']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    prometheus_ip = None
    for reservation in prometheus_instances['Reservations']:
        for instance in reservation['Instances']:
            prometheus_ip = instance.get('PrivateIpAddress')
            break
    
    if not prometheus_ip:
        print("Error: Instancia Prometheus no encontrada")
        return
    
    # Obtener AMI de Ubuntu
    images = ec2.describe_images(
        Filters=[
            {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*']},
            {'Name': 'owner-alias', 'Values': ['amazon']}
        ],
        Owners=['099720109477']
    )
    ami_id = sorted(images['Images'], key=lambda x: x['CreationDate'])[-1]['ImageId']
    
    # User data para Grafana
    grafana_userdata = f"""#!/bin/bash
apt update
apt install -y software-properties-common wget
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
apt update
apt install -y grafana
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Configurar datasource de Prometheus
sleep 30
curl -X POST -H "Content-Type: application/json" -d '{{
  "name": "Prometheus",
  "type": "prometheus",
  "url": "http://{prometheus_ip}:9090",
  "access": "proxy",
  "isDefault": true
}}' http://admin:admin@localhost:3000/api/datasources
"""
    
    # Crear instancia Grafana
    grafana_response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='vockey',
        SecurityGroupIds=[grafana_sg_id],
        SubnetId=subnet_id,
        UserData=grafana_userdata,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [{'Key': 'Name', 'Value': 'ec2-grafana'}]
            }
        ]
    )
    
    grafana_id = grafana_response['Instances'][0]['InstanceId']
    
    # Esperar a que la instancia esté corriendo
    print("Esperando a que Grafana esté corriendo...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[grafana_id])
    
    # Obtener IP pública
    instance = ec2.describe_instances(InstanceIds=[grafana_id])
    public_ip = instance['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'N/A')
    
    print(f"Grafana creado exitosamente!")
    print(f"Instance ID: {grafana_id}")
    print(f"Public IP: {public_ip}")
    print(f"Grafana UI: http://{public_ip}:3000")
    print(f"Usuario: admin, Contraseña: admin")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python add_grafana.py <vpc_id> <subnet_id>")
        sys.exit(1)
    
    vpc_id = sys.argv[1]
    subnet_id = sys.argv[2]
    add_grafana_instance(vpc_id, subnet_id)