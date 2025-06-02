import grpc
import time
import threading
import inventory_pb2
import inventory_pb2_grpc


def run():
    channel = grpc.insecure_channel("localhost:50051")
    stub = inventory_pb2_grpc.InventoryServiceStub(channel)

    def listen_alerts():
        print("\nЗапуск мониторинга алертов (порог: 10)...")
        try:
            for alert in stub.StreamStockAlerts(inventory_pb2.AlertRequest(threshold=10)):
                print(
                    f"\n[ALERT] Низкий запас: {alert.product_name} "
                    f"(ID: {alert.product_id}), Осталось: {alert.current_quantity}"
                )
        except Exception as e:
            print(f"Ошибка в стриме: {e}")

    alert_thread = threading.Thread(target=listen_alerts, daemon=True)
    alert_thread.start()

    # Список товаров для демонстрации работы
    products = [
        inventory_pb2.Product(id="p1", name="Ноутбук", quantity=20),
        inventory_pb2.Product(id="p2", name="Смартфон", quantity=15),
        inventory_pb2.Product(id="p3", name="Планшет", quantity=5),
    ]

    for product in products:
        try:
            existing = stub.GetProduct(inventory_pb2.ProductRequest(id=product.id))
            print(f"Продукт {product.name} уже существует: {existing.quantity} шт.")
        except grpc.RpcError as e:
            response = stub.AddProduct(product)
            if response.success:
                print(f"Добавлен продукт {product.name}: Успех")
            else:
                print(f"Продукт {response.id} уже существует: {response.name} ({response.quantity} шт.)")

    try:
        product = stub.GetProduct(inventory_pb2.ProductRequest(id="p1"))
        print(f"\nПолучен продукт: {product.name}, Количество: {product.quantity}")
    except grpc.RpcError as e:
        print(f"Ошибка получения продукта p1: {e.details()}")

    try:
        stub.UpdateStock(inventory_pb2.StockUpdateRequest(product_id="p1", delta=-5))
        print("Запасы p1 обновлены (-5)")
    except grpc.RpcError as e:
        print(f"Ошибка обновления запасов p1: {e.details()}")

    try:
        stub.UpdateStock(inventory_pb2.StockUpdateRequest(product_id="p3", delta=-3))
        print("Запасы p3 обновлены (-3)")
    except grpc.RpcError as e:
        print(f"Ошибка обновления запасов p3: {e.details()}")

    try:
        stub.UpdateStock(inventory_pb2.StockUpdateRequest(product_id="p1", delta=-50))
        print("Запасы p1 обновлены (-50)")
    except grpc.RpcError as e:
        print(f"Ошибка обновления запасов p1: {e.details()}")

    try:
        response = stub.ListProducts(inventory_pb2.Empty())
        print("\nТекущий список продуктов:")
        for p in response.products:
            print(f"- {p.name} (ID: {p.id}): {p.quantity} шт.")
    except grpc.RpcError as e:
        print(f"Ошибка получения списка: {e.details()}")

    try:
        response = stub.RemoveProduct(inventory_pb2.ProductRequest(id="p2"))
        if response.success:
            print("\nПродукт p2 успешно удален")
        else:
            print("\nПродукт p2 не найден")
    except grpc.RpcError as e:
        print(f"Ошибка удаления p2: {e.details()}")

    print("\nОжидание алертов... (нажмите Ctrl+C для выхода)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Клиент завершен")


if __name__ == "__main__":
    run()