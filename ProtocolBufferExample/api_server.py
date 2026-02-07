from fastapi import FastAPI
import generated.Toy_pb2 as Toy
import json

app = FastAPI(title="Toy API", description="API for serving toy data from Protocol Buffers")

def protobuf_to_dict(proto_obj):
    """Convert Protocol Buffer message to dictionary"""
    from google.protobuf.json_format import MessageToDict
    return MessageToDict(proto_obj)

def create_toy():
    """Create a toy instance using the existing example data"""
    toy = Toy.Toy()
    toy.name = "Toy"
    toy.description = "Toy description"
    toy.price = 100
    toy.company.name = "Company"
    toy.company.address = "Company address"
    toy.dimensions.extend([1, 2, 3])
    return toy

@app.get("/")
async def root():
    return {"message": "Toy API is running"}

@app.get("/toy")
async def get_toy():
    """Get toy data as JSON"""
    toy = create_toy()
    toy_dict = protobuf_to_dict(toy)
    return toy_dict

@app.get("/toy/protobuf")
async def get_toy_protobuf():
    """Get toy data as raw Protocol Buffer bytes"""
    toy = create_toy()
    toy_bytes = toy.SerializeToString()
    from fastapi.responses import Response
    return Response(content=toy_bytes, media_type="application/octet-stream")

@app.get("/toy/protobuf/base64")
async def get_toy_protobuf_base64():
    """Get toy data as base64 encoded Protocol Buffer string"""
    import base64
    toy = create_toy()
    toy_bytes = toy.SerializeToString()
    toy_b64 = base64.b64encode(toy_bytes).decode('utf-8')
    return {"toy_protobuf_base64": toy_b64}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
