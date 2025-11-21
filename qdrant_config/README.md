# Qdrant Configuration

This directory contains the Qdrant configuration file that sets the default vector dimension to 1024.

## Configuration Details

The [config.yaml](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/qdrant_config/config.yaml) file configures Qdrant with:

- Default vector size: 1024 dimensions (matching the embedding model)
- Distance metric: Cosine
- Storage type: rocksdb
- Performance optimizations

## How it works

When Qdrant starts with this configuration, new collections will automatically be created with 1024 dimensions, eliminating the need to run the fix script every time.

## Usage

The configuration is automatically mounted into the Qdrant container via the docker-compose.yml file:

```yaml
volumes:
  - ./qdrant_config:/qdrant/config:ro
```

This mounts the local [qdrant_config](file:///D:/WorkSpaces/GitHub/reach-moon/ppec_copilot/qdrant_config) directory to `/qdrant/config` in the container in read-only mode.