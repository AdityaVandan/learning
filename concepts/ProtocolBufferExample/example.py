import generated.Toy_pb2 as Toy

toy = Toy.Toy()
toy.name = "Toy"
toy.description = "Toy description"
toy.price = 100
toy.company.name = "Company"
toy.company.address = "Company address"
toy.dimensions.extend([1, 2, 3])

