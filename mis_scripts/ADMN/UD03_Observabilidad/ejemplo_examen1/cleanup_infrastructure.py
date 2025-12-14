#!/usr/bin/env python3
import boto3

def cleanup_monitoring_infrastructure():
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Buscar instancias por tags
    instances = ec2.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['ec2_a', 'prometheus', 'ec2-grafana']},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ]
    )
    
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        print(f"Terminando instancias: {instance_ids}")
        ec2.terminate_instances(InstanceIds=instance_ids)
        
        # Esperar a que terminen
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=instance_ids)
        print("Instancias terminadas")
    
    # Buscar y eliminar security groups
    sgs = ec2.describe_security_groups(
        Filters=[{'Name': 'group-name', 'Values': ['monitoring-sg', 'grafana-sg']}]
    )
    
    for sg in sgs['SecurityGroups']:
        if sg['GroupName'] != 'default':
            print(f"Eliminando Security Group: {sg['GroupId']}")
            ec2.delete_security_group(GroupId=sg['GroupId'])
    
    print("Infraestructura eliminada exitosamente!")

if __name__ == "__main__":
    cleanup_monitoring_infrastructure()