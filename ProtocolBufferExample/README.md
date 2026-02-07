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