import grpc
from concurrent import futures
import generated.Toy_pb2 as Toy
import generated.Toy_pb2_grpc as Toy_grpc
import base64

class ToyServiceImpl(Toy_grpc.ToyServiceServicer):
    def create_toy(self):
        """Create a toy instance using the existing example data"""
        toy = Toy.Toy()
        toy.name = "Toy"
        toy.description = "Toy description"
        toy.price = 100
        toy.company.name = "Company"
        toy.company.address = "Company address"
        toy.dimensions.extend([1, 2, 3])
        return toy

    def GetToy(self, request, context):
        """Get toy data as Protocol Buffer message"""
        toy = self.create_toy()
        return Toy.GetToyResponse(toy=toy)

    def GetToyProtobuf(self, request, context):
        """Get toy data as raw Protocol Buffer bytes"""
        toy = self.create_toy()
        toy_bytes = toy.SerializeToString()
        return Toy.GetToyProtobufResponse(toy_data=toy_bytes)

    def GetToyProtobufBase64(self, request, context):
        """Get toy data as base64 encoded Protocol Buffer string"""
        toy = self.create_toy()
        toy_bytes = toy.SerializeToString()
        toy_b64 = base64.b64encode(toy_bytes).decode('utf-8')
        return Toy.GetToyProtobufBase64Response(toy_protobuf_base64=toy_b64)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    Toy_grpc.add_ToyServiceServicer_to_server(ToyServiceImpl(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()