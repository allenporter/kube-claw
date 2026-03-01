import aiosqlite
import json

from kube_claw.domain.models import WorkspaceContext

from .table import BindingTable


class SQLiteBindingTable(BindingTable):
    """
    Persistent implementation of the BindingTable using SQLite and aiosqlite.
    """

    def __init__(self, db_path: str = "claw_v3.db"):
        self.db_path = db_path

    async def _init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bindings (
                    protocol TEXT,
                    channel_id TEXT,
                    author_id TEXT,
                    workspace_id TEXT,
                    pvc_name TEXT,
                    auth_profile TEXT,
                    metadata TEXT,
                    PRIMARY KEY (protocol, channel_id, author_id)
                )
            """)
            await db.commit()

    async def resolve_workspace(
        self, protocol: str, channel_id: str, author_id: str
    ) -> WorkspaceContext:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT workspace_id, pvc_name, auth_profile, metadata FROM bindings WHERE protocol = ? AND channel_id = ? AND author_id = ?",
                (protocol, channel_id, author_id),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return WorkspaceContext(
                        workspace_id=row[0],
                        pvc_name=row[1],
                        auth_profile=json.loads(row[2]),
                        metadata=json.loads(row[3]),
                    )

        # JIT Provisioning (Mock for now, returns a default)
        workspace_id = f"ws-{protocol}-{author_id}"
        context = WorkspaceContext(workspace_id=workspace_id)
        await self.update_binding(protocol, channel_id, author_id, context)
        return context

    async def update_binding(
        self, protocol: str, channel_id: str, author_id: str, context: WorkspaceContext
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO bindings (protocol, channel_id, author_id, workspace_id, pvc_name, auth_profile, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    protocol,
                    channel_id,
                    author_id,
                    context.workspace_id,
                    context.pvc_name,
                    json.dumps(context.auth_profile),
                    json.dumps(context.metadata),
                ),
            )
            await db.commit()
