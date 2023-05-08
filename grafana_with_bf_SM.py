from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_ecs_patterns as ecs_patterns,
    core
)


class GrafanaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "GrafanaVPC", max_azs=2)

        # Create a RDS Aurora database instance
        database = rds.DatabaseInstance(
            self,
            "GrafanaDB",
            engine=rds.DatabaseInstanceEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_5_7_12),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL),
            vpc=vpc,
            allocated_storage=10,
            database_name="grafana",
            credentials=rds.Credentials.from_generated_secret("admin"),
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # Create a secret to store the database credentials
        secret = secretsmanager.Secret(self, "GrafanaDBSecret")
        secret.grant_read(database)

        # Create an ECS Fargate cluster
        cluster = ecs.Cluster(self, "GrafanaCluster", vpc=vpc)

        # Create a task definition
        task_definition = ecs.FargateTaskDefinition(self, "GrafanaTaskDefinition")
        container = task_definition.add_container(
            "GrafanaContainer",
            image=ecs.ContainerImage.from_registry("grafana/grafana:latest"),
            environment={
                "GF_DATABASE_TYPE": "mysql",
                "GF_DATABASE_HOST": database.db_instance_endpoint_address,
                "GF_DATABASE_NAME": "grafana",
                "GF_DATABASE_USER": secret.secret_value_from_json("username").to_string(),
                "GF_DATABASE_PASSWORD": secret.secret_value_from_json("password").to_string()
            }
        )
        container.add_port_mappings(ecs.PortMapping(container_port=3000))

        # Create a Fargate service
        ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "GrafanaService",
            cluster=cluster,
            task_definition=task_definition,
            public_load_balancer=True
        )


app = core.App()
GrafanaStack(app, "GrafanaStack")
app.synth()
