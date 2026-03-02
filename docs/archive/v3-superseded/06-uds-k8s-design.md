# Design: Unix Domain Sockets (UDS) in Kubernetes

This document explains the mechanism for using Unix Domain Sockets (UDS) as the IPC (Inter-Process Communication) layer between the Claw Host and the Worker Sandbox in a Kubernetes environment.

## 1. The "Shared File" Pattern
In Kubernetes, two containers in the same Pod can share a filesystem using an `emptyDir` volume. Since a Unix Socket is represented as a file on the filesystem, this volume becomes the "patch panel" where they connect.

### How it Works
1.  **Shared Volume**: A volume of type `emptyDir` is defined in the Pod spec.
2.  **Mounting**: Both the **Host** container and the **Worker** container mount this volume at the same path (e.g., `/rpc`).
3.  **Socket Creation**: The Worker starts an RPC server and creates a socket file at `/rpc/worker.sock`.
4.  **Connection**: The Host (acting as a client) connects to the file at `/rpc/worker.sock`.

## 2. Example Pod Specification (Conceptual)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: claw-lane-xyz
spec:
  containers:
  - name: worker-sandbox
    image: claw-worker:latest
    volumeMounts:
    - name: rpc-socket
      mountPath: /rpc
    env:
    - name: SOCKET_PATH
      value: "/rpc/worker.sock"

  - name: host-gateway
    image: claw-host:latest
    volumeMounts:
    - name: rpc-socket
      mountPath: /rpc
    env:
    - name: SOCKET_PATH
      value: "/rpc/worker.sock"

  volumes:
  - name: rpc-socket
    emptyDir: {}
```

## 3. Why This "Really Works"
*   **Performance**: Data is copied directly between the memory spaces of the two processes by the Linux kernel. It never touches the network interface (eth0), iptables, or the kube-proxy.
*   **Security**: The socket file is only visible to the processes that have the `/rpc` volume mounted. It is completely invisible to any other Pod on the node or the network.
*   **Lifecycle**: When the Pod is deleted, the `emptyDir` and the socket file are automatically cleaned up by Kubernetes.

## 4. Implementation Details (Python)

### Worker (Server)
```python
import asyncio
import os

async def handle_client(reader, writer):
    data = await reader.read(100)
    # Process A2A Protocol message...
    writer.write(b"ACK")
    await writer.drain()
    writer.close()

async def main():
    socket_path = os.getenv("SOCKET_PATH", "/rpc/worker.sock")
    server = await asyncio.start_unix_server(handle_client, path=socket_path)
    async with server:
        await server.serve_forever()
```

### Host (Client)
```python
import asyncio
import os

async def send_task(message):
    socket_path = os.getenv("SOCKET_PATH", "/rpc/worker.sock")
    reader, writer = await asyncio.open_unix_connection(socket_path)
    writer.write(message.encode())
    await writer.drain()
    # Read response...
    writer.close()
```

## 5. Security Note: Permissions
Because UDS uses the filesystem, we can use `securityContext` in Kubernetes to ensure the socket file has the correct ownership (`runAsUser` / `fsGroup`), preventing unauthorized processes within the container from accessing the socket if the container is multi-process.
