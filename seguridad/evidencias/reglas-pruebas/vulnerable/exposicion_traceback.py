import traceback
from flask import jsonify


def handler(e):
    return jsonify(
        {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "config": {"db": "/data/tickets.db"},
        }
    ), 500