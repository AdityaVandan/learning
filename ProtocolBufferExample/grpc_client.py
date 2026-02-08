import grpc
import generated.Toy_pb2 as Toy
import generated.Toy_pb2_grpc as Toy_grpc

def main():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = Toy_grpc.ToyServiceStub(channel)
        
        # Get toy as protobuf
        response = stub.GetToy(Toy.GetToyRequest())
        print(f"Toy name: {response.toy.name}")
        
        # Get toy as bytes
        response = stub.GetToyProtobuf(Toy.GetToyRequest())
        print(f"Raw bytes length: {len(response.toy_data)}")
        
        # Get toy as base64
        response = stub.GetToyProtobufBase64(Toy.GetToyRequest())
        print(f"Base64: {response.toy_protobuf_base64[:50]}...")

if __name__ == '__main__':
    main()