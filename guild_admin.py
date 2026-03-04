#!/usr/bin/env python3
"""Guild management CLI. Run inside the Docker container.

Usage:
  python3 guild_admin.py add "GuildName"           # prompts for password
  python3 guild_admin.py add "GuildName" -p temppass
  python3 guild_admin.py reset "GuildName"          # prompts for new password
  python3 guild_admin.py reset "GuildName" -p newpass
  python3 guild_admin.py list
"""

import argparse
import getpass
import bcrypt
from database import get_connection


def add_guild(name, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM guilds WHERE name = ?", (name,))
    if cursor.fetchone():
        conn.close()
        print(f"Guild '{name}' already exists.")
        return

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cursor.execute("INSERT INTO guilds (name, password) VALUES (?, ?)", (name, hashed))
    conn.commit()
    conn.close()
    print(f"Guild '{name}' created. Share the password with the guild leader.")


def reset_password(name, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM guilds WHERE name = ?", (name,))
    if not cursor.fetchone():
        conn.close()
        print(f"Guild '{name}' not found.")
        return

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cursor.execute("UPDATE guilds SET password = ? WHERE name = ?", (hashed, name))
    conn.commit()
    conn.close()
    print(f"Password updated for '{name}'.")


def list_guilds():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT g.name, g.password,
               (SELECT COUNT(*) FROM guild_members gm WHERE gm.guild_id = g.id) as members
        FROM guilds g ORDER BY g.name
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No guilds found.")
        return

    for r in rows:
        has_pw = "yes" if r["password"] else "NO"
        print(f"  {r['name']:20s}  members: {r['members']:3d}  password: {has_pw}")


def main():
    parser = argparse.ArgumentParser(description="Guild management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a new guild")
    add_p.add_argument("name", help="Guild name")
    add_p.add_argument("-p", "--password", help="Password (prompts if omitted)")

    reset_p = sub.add_parser("reset", help="Reset a guild's password")
    reset_p.add_argument("name", help="Guild name")
    reset_p.add_argument("-p", "--password", help="New password (prompts if omitted)")

    sub.add_parser("list", help="List all guilds")

    args = parser.parse_args()

    if args.command == "add":
        pw = args.password or getpass.getpass("Password: ")
        add_guild(args.name, pw)
    elif args.command == "reset":
        pw = args.password or getpass.getpass("New password: ")
        reset_password(args.name, pw)
    elif args.command == "list":
        list_guilds()


if __name__ == "__main__":
    main()