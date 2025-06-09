import os
import sys
import snowflake.connector
from cryptography.hazmat.primitives import serialization

def load_private_key(key_path: str, passphrase: str | None = None):
    """Load an RSA private key from a file."""
    with open(key_path, "rb") as f:
        key_data = f.read()
    return serialization.load_pem_private_key(
        key_data,
        password=passphrase.encode() if passphrase else None,
    )

def connect_snowflake():
    """Establish a Snowflake connection using RSA key authentication."""
    user = os.getenv("SNOWFLAKE_USER")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    private_key_pass = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    role = os.getenv("SNOWFLAKE_ROLE", "")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "")

    if not (user and account and private_key_path):
        raise RuntimeError(
            "SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, and SNOWFLAKE_PRIVATE_KEY_PATH must be set"
        )

    pk = load_private_key(private_key_path, private_key_pass)
    ctx = snowflake.connector.connect(
        user=user,
        account=account,
        private_key=pk,
        role=role or None,
        warehouse=warehouse or None,
    )
    return ctx

def validate_read_access(ctx):
    cur = ctx.cursor()
    try:
        cur.execute(
            "SELECT table_schema FROM information_schema.schemata ORDER BY table_schema"
        )
        schemas = [row[0] for row in cur.fetchall()]
        for schema in schemas:
            print(f"\nSchema: {schema}")
            cur.execute(
                f"SELECT table_name FROM {schema}.information_schema.tables WHERE table_type='BASE TABLE' ORDER BY table_name"
            )
            tables = [row[0] for row in cur.fetchall()]
            for table in tables:
                fq_table = f"{schema}.{table}"
                try:
                    cur.execute(f"SELECT 1 FROM {fq_table} LIMIT 1")
                    print(f"  OK: {fq_table}")
                except snowflake.connector.errors.Error as e:
                    print(f"  FAIL: {fq_table} - {e}")
    finally:
        cur.close()


def main():
    try:
        ctx = connect_snowflake()
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    try:
        validate_read_access(ctx)
    finally:
        ctx.close()


if __name__ == "__main__":
    main()
