import grpc
from concurrent import futures
import time
import json
import os
from pathlib import Path
import threading
from datetime import datetime
import inventory_pb2
import inventory_pb2_grpc


class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def __init__(self):
        self.storage_file = "storage.json"
        self.data = {"products": {}, "stock_changes": []}
        self.alerts = {}
        self.lock = threading.Lock()
        self.load_data()

    def load_data(self):
        if Path(self.storage_file).exists():
            with open(self.storage_file, "r") as f:
                self.data = json.load(f)

    def save_data(self):
        with open(self.storage_file, "w") as f:
            json.dump(self.data, f)

    def AddProduct(self, request, context):
        with self.lock:
            if request.id in self.data["products"]:
                return inventory_pb2.ProductResponse(id=request.id, success=False)

            self.data["products"][request.id] = {
                "name": request.name,
                "quantity": request.quantity
            }
            self.data["stock_changes"].append({
                "product_id": request.id,
                "delta": request.quantity,
                "timestamp": datetime.now().isoformat()
            })
            self.save_data()
            return inventory_pb2.ProductResponse(id=request.id, success=True)

    def GetProduct(self, request, context):
        product = self.data["products"].get(request.id)
        if not product:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return inventory_pb2.Product()
        return inventory_pb2.Product(
            id=request.id,
            name=product["name"],
            quantity=product["quantity"]
        )

    def UpdateStock(self, request, context):
        with self.lock:
            product = self.data["products"].get(request.product_id)
            if not product:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return inventory_pb2.Product()

            new_quantity = product["quantity"] + request.delta
            if new_quantity < 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                return inventory_pb2.Product()

            product["quantity"] = new_quantity
            self.data["stock_changes"].append({
                "product_id": request.product_id,
                "delta": request.delta,
                "timestamp": datetime.now().isoformat()
            })
            self.save_data()

            if request.product_id in self.alerts:
                self.alerts[request.product_id]["sent"] = False

            return inventory_pb2.Product(
                id=request.product_id,
                name=product["name"],
                quantity=product["quantity"]
            )

    def RemoveProduct(self, request, context):
        with self.lock:
            if request.id not in self.data["products"]:
                return inventory_pb2.RemoveResponse(success=False)

            del self.data["products"][request.id]
            self.save_data()
            return inventory_pb2.RemoveResponse(success=True)

    def ListProducts(self, request, context):
        products = [
            inventory_pb2.Product(id=pid, **data)
            for pid, data in self.data["products"].items()
        ]
        return inventory_pb2.ListProductsResponse(products=products)

    def StreamStockAlerts(self, request, context):
        threshold = request.threshold
        while True:
            time.sleep(3)
            with self.lock:
                for pid, product in self.data["products"].items():
                    if product["quantity"] < threshold:
                        if pid not in self.alerts or not self.alerts[pid]["sent"]:
                            self.alerts[pid] = {
                                "sent": True,
                                "threshold": threshold
                            }
                            yield inventory_pb2.StockAlert(
                                product_id=pid,
                                product_name=product["name"],
                                current_quantity=product["quantity"]
                            )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    print("Сервер запущен на порту 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()