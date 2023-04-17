from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_iam as iam,
    aws_logs as logs,
    core
)

class GrafanaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "GrafanaVpc",
            max_azs=2,
            nat_gateways=1
        )

        # Create a task definition for Grafana
        task_definition = ecs.TaskDefinition(self, "GrafanaTaskDefinition",
            compatibility=ecs.Compatibility.FARGATE,
            cpu='256',
            memory_mib='512',
            family='grafana'
        )

        # Create a container for Grafana
        container = task_definition.add_container("grafana",
            image=ecs.ContainerImage.from_registry("grafana/grafana"),
            logging=ecs.LogDriver.aws_logs(stream_prefix='grafana'),
            environment={
                "GF_DATABASE_TYPE": "sqlite3",
                "GF_DATABASE_PATH": "/var/lib/grafana/grafana.db",
                "GF_DATABASE_PASSWORD": "my_password",
            }
        )

        # Create a volume for Grafana data
        volume = ecs.Volume(name='grafana-data')
        task_definition.add_volume(volume)

        # Mount the volume to the Grafana container
        container.add_mount_points(ecs.MountPoint(
            container_path='/var/lib/grafana',
            source_volume=volume.name,
            read_only=False
        ))

        # Create an ECS cluster
        cluster = ecs.Cluster(self, "GrafanaCluster",
            vpc=vpc
        )

        # Create a Fargate service for Grafana
        service = ecs.FargateService(self, "GrafanaFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1
        )

        # Create a security group for Grafana
        security_group = ec2.SecurityGroup(self, "GrafanaSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True
        )

        # Add inbound rules to the security group
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4('0.0.0.0/0'),
            connection=ec2.Port.tcp(80),
            description='Allow HTTP traffic'
        )
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4('0.0.0.0/0'),
            connection=ec2.Port.tcp(443),
            description='Allow HTTPS traffic'
        )

        # Output the Grafana URL
        core.CfnOutput(self, "GrafanaUrl",
            value=f"http://{service.load_balancer.load_balancer_dns_name}"
        )

app = core.App()
GrafanaStack(app, "grafana-stack")
app.synth()
