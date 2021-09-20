from argparse import ArgumentParser
import boto3
import config
import csv

import os
import pathlib
import re

from pprint import pprint
import socket


def check_sg_exposed(sg):
    cidr_block = '0.0.0.0/0'
    for ip in sg['IpRanges']:
        if ip['CidrIp'] == cidr_block:
            return True
    return False


def get_ec2_ports_exposed(ec2_client, sgs_list):
    exposed_ports = []
    sg_list = ec2_client.describe_security_groups(GroupIds=sgs_list)
    for sg in sg_list['SecurityGroups']:
        for ip_permissions in sg['IpPermissions']:
            if check_sg_exposed(ip_permissions):
                if 'FromPort' and 'ToPort' in ip_permissions:
                    protocol = ip_permissions['IpProtocol']
                    if protocol == "-1":
                        protocol = "all"
                    port = "{0}/{1}".format(protocol, str(ip_permissions["FromPort"]))
                    if ip_permissions['FromPort'] != ip_permissions['ToPort']:
                        port = "{0}/{1}-{2}".format(protocol, str(ip_permissions['FromPort']), str(ip_permissions['ToPort']))
                    exposed_ports.append(port)
    return exposed_ports


def get_elb_public_ips(session):
    ec2_client = session.client('ec2')

    exposed_elb = []
    elb_v1 = session.client('elb')
    elb_v2 = session.client('elbv2')

    try:
        lbs_v1 = elb_v1.describe_load_balancers()
        lbs_v2 = elb_v2.describe_load_balancers()
    except Exception:
        print("No Load Balancers found")
        raise Exception

    for lbs in lbs_v1['LoadBalancerDescriptions']:
        if not re.match(r'^internal', lbs['DNSName']):
            sg_list = lbs['SecurityGroups']
            exposed_elb.append(
            {
                'Resource Name': 'elb',
                'Service Identifier': lbs['LoadBalancerName'],
                'Public DNS/IP': socket.gethostbyname(lbs['DNSName']),
                'Ports Exposed': get_ec2_ports_exposed(ec2_client, sg_list),
                'Security Group': lbs['SecurityGroups']
            }
        )

    for loadB_v2 in  lbs_v2['LoadBalancers']:
        if re.match(r'internet-facing', loadB_v2['Scheme']):
            sg_list = loadB_v2['SecurityGroups']
            exposed_elb.append(
            {
                'Resource Name': 'elb-v2',
                'Service Identifier': loadB_v2['LoadBalancerName'],
                'Public DNS/IP': socket.gethostbyname(loadB_v2['DNSName']),
                'Ports Exposed': get_ec2_ports_exposed(ec2_client, sg_list),
                'Security Group': loadB_v2['SecurityGroups']
            }
        )
    return exposed_elb


def get_name_ec2(tags):
    for tag in tags:
        if tag['Key'] == 'Name':
            return tag['Value']
    return ""


def get_sg_ec2(sg_group):
    sg = []
    for group in sg_group:
        sg.append(group['GroupId'])
    return sg


def get_ec2_public_ips(session):
    ec2_exposed = []
    ec2_client = session.client('ec2')
    try: 
        instances = ec2_client.describe_instances(Filters=[{
            'Name': 'instance-state-name',
            'Values': ['running', 'stopped', 'stopping', 'pending']}])
    except Exception as e:
        print("EC2 client unable to describe instances")
        raise Exception
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            if 'PublicIpAddress' in instance:
                sg_list = get_sg_ec2(instance['SecurityGroups'])
                ec2_exposed.append(
                    {
                        'Resource Name': "ec2",
                        'Service Identifier': get_name_ec2(instance['Tags']),
                        'Public DNS/IP': instance["PublicIpAddress"],
                        'Ports Exposed': get_ec2_ports_exposed(ec2_client, sg_list),
                        'Security Group': sg_list

                    }
                )
    return ec2_exposed


def get_sgs_rds(sg_group):
    sg = []
    for group in sg_group:
        sg.append(group['VpcSecurityGroupId'])
    return sg


def get_rds_public_ips(session):
    exposed_rds = []
    rds_client = session.client('rds')
    ec2_client = session.client('ec2')

    try:
        instances = rds_client.describe_db_instances()
    except Exception as e:
        print("RDS client unable to describe database instances")
        raise Exception
    
    for db in instances['DBInstances']:
        if db['PubliclyAccessible']:
            ip = socket.gethostbyname(db['Endpoint']['Address'])
            sg_list = get_sgs_rds(db['VpcSecurityGroups'])
            exposed_rds.append(
                {
                    'Resource Name': 'rds',
                    'Service Identifier': db['DBInstanceIdentifier'],
                    'Public DNS/IP': ip,
                    'Ports Exposed': get_ec2_ports_exposed(ec2_client, sg_list),
                    'Security Group': sg_list
                }
            )
    return exposed_rds


def build_csv(data, headers):
    path = r"<Insert File Dir>"
    plpath = pathlib.PurePath(path)
    filename = str(plpath.name) + ".csv"
    csv_filename = os.path.join(path, filename)
    with open(csv_filename, 'w') as file:
        writer = csv.DictWriter(file,  delimiter=',', fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def parse_args():
    parser = ArgumentParser(description='Review AWS Accounts for exposed Public IP/Ports')
    parser.add_argument('--profile', type=str, required=False,
                        help='Specify AWS Profiles, stored in ~/.aws./credentials')
    return parser.parse_args()


def main():
    exposed_services = []
    args = parse_args()
    profile = args.profile

    if profile:
        aws_profile = profile
        print(f"Profile has been set to: {aws_profile} \n")
    else:
        aws_profile = config.profile_name
        print(f"Profile not set, using default from Config: {aws_profile} \n")

    for aws_region in config.regions:
        print(f"Checking AWS Region: {aws_region}")
        try:
            session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        except Exception as e:
            print(f"Failed to initialze boto session, Error: \n {e}")
        try: 
            print("Checking EC2 for exposed IPs / Ports....")
            exposed_services += get_ec2_public_ips(session)
        except Exception as e:
            print(f"Unable to check EC2 instances, Error: \n {e})")

        try:
            print("Checking RDS for exposed IPs / Ports....")
            exposed_services += get_rds_public_ips(session)
        except Exception as e:
            print(f"Unable to check RDS databases, Error: \n {e})")

        try:
            print("Checking Load Balancers for exposed IPs / Ports.... \n")
            exposed_services += get_elb_public_ips(session)
        except Exception as e:
            print(f"Unable to check load balancers, Error: \n {e})")

    print("---------------------------------------------\n Generating CSV File for Review..")
    header_row = ['Resource Name', 'Service Identifier', 'Public DNS/IP', 'Ports Exposed', 'Security Group']
    build_csv(exposed_services, header_row)
    print("CSV File Generated.")

if __name__ == "__main__":
    main()
