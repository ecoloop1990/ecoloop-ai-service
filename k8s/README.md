# Kubernetes Deployment

This directory contains Kubernetes configuration files for deploying the Ecoloop AI Service.

## Files

- `deployment.yaml` - Main deployment configuration with 2 replicas, resource limits, and health probes
- `service.yaml` - ClusterIP service exposing the application on port 80
- `configmap.yaml` - Configuration for environment variables (ENVIRONMENT, LOG_LEVEL)
- `hpa.yaml` - Horizontal Pod Autoscaler (2-5 replicas, 70% CPU target)

## Deployment

### Prerequisites

- Kubernetes cluster (EKS recommended)
- kubectl configured
- Docker image built and pushed to registry

### Steps

1. Build and push Docker image:
```bash
docker build -t ecoloop-ai-service:latest .
docker tag ecoloop-ai-service:latest <your-registry>/ecoloop-ai-service:latest
docker push <your-registry>/ecoloop-ai-service:latest
```

2. Update image in `deployment.yaml` if using a registry:
```yaml
image: <your-registry>/ecoloop-ai-service:latest
```

3. Apply configurations:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

4. Verify deployment:
```bash
kubectl get pods -l app=ecoloop-ai
kubectl get svc ecoloop-ai-service
kubectl get hpa ecoloop-ai-hpa
```

## Service Access

The service is accessible within the cluster at:
```
http://ecoloop-ai-service:80/analyze
```

## Health Checks

- **Liveness Probe**: `/health` endpoint, checks every 10s after 30s initial delay
- **Readiness Probe**: `/health` endpoint, checks every 5s after 10s initial delay

## Scaling

The HPA automatically scales based on CPU utilization:
- **Min replicas**: 2
- **Max replicas**: 5
- **Target CPU**: 70%

## Resource Limits

- **CPU**: 500m limit, 250m request
- **Memory**: 512Mi limit, 256Mi request

## Configuration

Environment variables are managed via ConfigMap:
- `ENVIRONMENT`: production
- `LOG_LEVEL`: info

To update configuration:
```bash
kubectl edit configmap ecoloop-ai-config
kubectl rollout restart deployment ecoloop-ai
```

