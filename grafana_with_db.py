from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as sm,
    aws_securitygroup as sg,
    aws_ecs as ecs,
    core,
)

class GrafanaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC for the Grafana resources
        vpc = ec2.Vpc(self, "GrafanaVpc", max_azs=2)

        # Create a security group for the Grafana container
        sg_container = sg.SecurityGroup(self, "GrafanaContainerSG", vpc=vpc)

        # Allow inbound traffic on port 3000 from anywhere
        sg_container.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(3000))

        # Create an S3 bucket to store Grafana data
        bucket = s3.Bucket(self, "GrafanaBucket")

        # Deploy a sample dashboard to the S3 bucket
        s3deploy.BucketDeployment(self, "GrafanaDashboard",
            sources=[s3deploy.Source.asset("dashboard")],
            destination_bucket=bucket,
        )

        # Create a Secrets Manager secret to store the AWS credentials
        secret = sm.Secret(self, "GrafanaCredentials")

        # Define an ECS task definition for the Grafana container
        task_definition = ecs.TaskDefinition(self, "GrafanaTaskDefinition",
            compatibility=ecs.Compatibility.FARGATE,
            cpu='512',
            memory_mib='1024',
        )

        # Add a container to the task definition
        container = task_definition.add_container("grafana",
            image=ecs.ContainerImage.from_registry("my-grafana-image"),
            memory_reservation_mib=512,
            logging=ecs.LogDriver.aws_logs(stream_prefix="grafana"),
            secrets={
                'AWS_ACCESS_KEY_ID': ecs.Secret.from_secrets_manager(secret, 'aws_access_key_id'),
                'AWS_SECRET_ACCESS_KEY': ecs.Secret.from_secrets_manager(secret, 'aws_secret_access_key'),
            },
            environment={
                'GF_SECURITY_ADMIN_PASSWORD': 'mysecretpassword',
                'GF_INSTALL_PLUGINS': 'grafana-sqlite-datasource',
                'GF_DATABASE_TYPE': 'sqlite3',
                'GF_DATABASE_PATH': '/var/lib/grafana/grafana.db',
                'GF_USERS_ALLOW_SIGN_UP': 'false',
                'GF_USERS_DEFAULT_THEME': 'light',
            },
        )

        # Add the container to the task definition
        container.add_port_mappings(ecs.PortMapping(container_port=3000))

        # Define an ECS service for the Grafana container
        service = ecs.FargateService(self, "GrafanaService",
            cluster=ecs.Cluster(self, "GrafanaCluster",
