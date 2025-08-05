from flask import Blueprint , send_file


helper_bp = Blueprint('helper',__name__)




@helper_bp.route("/help")
def help():
   return send_file("assets/data.txt", as_attachment=True)