from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_rds as rds,
    core,
)

class GrafanaStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Define a VPC for the ECS cluster
        vpc = ec2.Vpc(self, "GrafanaVpc",
            max_azs=2,
            nat_gateways=1)

        # Define a task definition for the Grafana container
        grafana_task = ecs.FargateTaskDefinition(self, "GrafanaTask",
            cpu=256,
            memory_limit_mib=512)

        grafana_container = grafana_task.add_container("GrafanaContainer",
            image="grafana/grafana:latest",
            port_mappings=[ecs.PortMapping(container_port=3000)],
            environment={
                "GF_INSTALL_PLUGINS": "grafana-piechart-panel,grafana-clock-panel"
            })

        # Define a service for the Grafana container
        grafana_service = ecs.FargateService(self, "GrafanaService",
            cluster=ecs.Cluster(self, "GrafanaCluster", vpc=vpc),
            task_definition=grafana_task,
            desired_count=1,
            platform_version=ecs.FargatePlatformVersion.VERSION1_4)

        # Create an Application Load Balancer to expose the Grafana service
        lb = elbv2.ApplicationLoadBalancer(self, "GrafanaLoadBalancer",
            vpc=vpc,
            internet_facing=True)

        listener = lb.add_listener("GrafanaListener",
            port=80,
            open=True)

        listener.add_targets("GrafanaTarget",
            targets=[grafana_service],
            port=3000)

        # Output the Grafana URL for convenience
        core.CfnOutput(self, "GrafanaUrl",
            value="http://{}".format(lb.load_balancer_dns_name))
