from flask import Flask, request, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
        MessageEvent, 
        TextMessage, 
        TextSendMessage, 
        StickerMessage, A
        ConfirmTemplate,
        MessageAction,
        TemplateSendMessage
)
from copy import deepcopy
from datetime import datetime
import os
import random

import config
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)

CHANNEL_ACCESS_TOKEN = config.CHANNEL_ACCESS_TOKEN
CHANNEL_SECRET = config.CHANNEL_SECRET


line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

class ShoppingList(db.Model):
    no = db.Column(db.Integer, primary_key=True)
    utype = db.Column(db.String(10), nullable=False)
    uid = db.Column(db.String(100), nullable=False)
    item = db.Column(db.String(100), nullable=False)
    register_date = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, utype, uid, item, register_date):
        self.utype = utype
        self.uid = uid
        self.item = item
        self.register_date = register_date
    
    def __repr__(self):
        return "<Shopping-List> Type: {}, ID: {}, Item: {}, Date: {}".format(self.utype, self.uid, self.item, self.register_date)

db.create_all()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


operators = {
        "リスト",
        "追加",
        "削除",
        "全削除",
        "showdb"
}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if event.reply_token=="00000000000000000000000000000000":
        return

    # --- extract operation and message-object ---
    user_message = deepcopy(event.message.text)
    user_message = user_message.split("\n")
    
    operate = ""
    if user_message[0] in operators:
        operate = user_message.pop(0)
    elif user_message[-1] in operators:
        operate = user_message.pop()
    
    # --- extract type ---
    utype = event.source.type

    # --- extract uid(user_id or group_id or room_id) ---
    if utype=="user":
        uid = event.source.user_id
    if utype=="group":
        uid = event.source.group_id
    if utype=="room":
        uid = event.source.room_id
    if uid is None:
        return
    
    
    if operate=="リスト":
        return_message = [v.item for v in db.session.query(ShoppingList).filter_by(uid=uid).all()]
        if len(return_message)==0:
            return_message = ["リストにアイテムがありません"]

    elif operate=="追加":
        for item in user_message:
            db.session.add(ShoppingList(utype, uid, item, datetime.now()))
        db.session.commit()
        return_message = ["追加しました"]
    
    elif operate=="削除":
        for u in user_message:
            item = db.session.query(ShoppingList).filter(
                    ShoppingList.uid==uid,
                    ShoppingList.item==u
                    ).first()
            db.session.delete(item)
        db.session.commit()
        return_message = ["削除しました"]
    
    elif operate=="全削除":
        db.session.query(ShoppingList).filter(ShoppingList.uid==uid).delete()
        db.session.commit()
        return_message = ["リストを全て削除しました"]
    
    elif operate=="確認":
        line_bot_api.reply_message(
                event.reply_token,
                confirm_template = ConfirmTemplate(text="Do it?", actions=[
                    MessageAction(label="Yes", text="Yes!"),
                    MessageAction(label="No", text="No!")
                ])
        )

    # --- Administrator ---
    elif (uid in config.ADMIN_ID) and operate=="showdb":
        return_message = [str(v) for v in db.session.query(ShoppingList).order_by(ShoppingList.register_date).all()]
        if len(return_message)==0:
            return_message = ["データベースが空です"]

    else:
        return

    line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(return_message))
    )

@handler.add(MessageEvent, message=StickerMessage)
def handle_video(event):
    if event.reply_token=="ffffffffffffffffffffffffffffffff":
        return
    line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_random_text())
    )


def response_random_text():
    txt = [
            "そのスタンプかわいい！",
            "僕のことナメてるの？",
            "いつもかわいいスタンプを送ってくれて嬉しいよ",
            "疲れてるのかな。ゆっくり休んでね",
            "君の名は....",
            "そのスタンプによると、今晩のオススメのおかずはエビチリです",
            "そのスタンプによると、今晩のオススメのおかずはチャーハンです",
            "そのスタンプによると、今晩のオススメのおかずはうなぎです",
            "そのスタンプによると、今晩のオススメのおかずは鶏ハムです",
            "そのスタンプによると、今晩のオススメのおかずは肉じゃがです"
    ]
    return random.choice(txt)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)