from aws_cdk import core as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk.aws_ec2 import Port

class GrafanaStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC with two availability zones
        vpc = ec2.Vpc(self, 'VPC', max_azs=2)

        # Create a security group for the ECS tasks
        task_sg = ec2.SecurityGroup(self, 'TaskSG', vpc=vpc)
        task_sg.add_ingress_rule(ec2.Peer.any_ipv4(), port_range=Port.tcp(3000), description='Allow Grafana traffic')

        # Create a security group for the RDS instance
        rds_sg = ec2.SecurityGroup(self, 'RDSSG', vpc=vpc)
        rds_sg.add_ingress_rule(task_sg, port_range=Port.tcp(3306), description='Allow RDS traffic from the ECS tasks')

        # Create the RDS Aurora Serverless instance
        aurora = rds.ServerlessCluster(self, 'Aurora', engine=rds.DatabaseClusterEngine.AURORA_MYSQL,
                                       vpc=vpc, security_groups=[rds_sg])

        # Create the Secret Manager secret for the RDS instance password
        secret = secretsmanager.Secret(self, 'RDSSecret', generate_secret_string=secretsmanager.SecretStringGenerator(
            exclude_punctuation=True))

        # Create the ECS Fargate task definition with the Grafana container and environment variables
        task_definition = ecs.FargateTaskDefinition(self, 'TaskDef')
        container = task_definition.add_container('grafana',
                                                   image=ecs.ContainerImage.from_registry('grafana/grafana'),
                                                   environment={
                                                       'GF_INSTALL_PLUGINS': 'grafana-clock-panel',
                                                       'GF_DATABASE_TYPE': 'mysql',
                                                       'GF_DATABASE_HOST': aurora.cluster_endpoint.hostname,
                                                       'GF_DATABASE_NAME': 'grafana',
                                                       'GF_DATABASE_USER': 'admin',
                                                       'GF_DATABASE_PASSWORD': secret.secret_value_from_json('password').to_string()
                                                   })
        container.add_port_mappings(ecs.PortMapping(container_port=3000))

        # Create the ECS Fargate service with the task definition and security group
        ecs_patterns.ApplicationLoadBalancedFargateService(self, 'Service',
                                                            task_definition=task_definition,
                                                            assign_public_ip=True,
                                                            security_groups=[task_sg],
                                                            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE))
