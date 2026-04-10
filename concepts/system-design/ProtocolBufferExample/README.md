# Protocol Buffer Example

## Setup

```bash
brew install protobuf
```

## Generate Python code

```bash
protoc --proto_path=schema --python_out=generated schema/Toy.proto
```

## Run Python code

```bash
python3 generated/Toy_pb2.py
```

## Run gRPC server

```bash
python3 grpc_example_server.py
```

## Run gRPC client

```bash
python3 grpc_client.py
```

## For generating gRPC code

```bash
protoc --proto_path=schema --python_out=generated --grpc_python_out=generated schema/Toy.proto
```

### For generating gRPC code with Python 3.13 compatibility

```bash
 python -m grpc_tools.protoc -I./schema --python_out=./generated --grpc_python_out=./generated ./schema/Toy.proto
```

### For generating gRPC code with Python 3.13 compatibility

```bash
protoc --proto_path=schema --python_out=generated --grpc_python_out=generated schema/Toy.proto
```