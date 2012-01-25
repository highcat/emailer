#! /usr/bin/env python
# -*- coding: utf-8 -*-
from emailer import Account, Attachment, Email

account = Account(
    email='emailer_test@localhost',
    fromname=u'Emailer test',
    server='localhost',
    )

attach_content = u"Text file attachment\n\nJust to test if it works\n\nРусский язык должен быть в правильной кодирове"
attach_content = attach_content.encode('utf-8')

txt_attachment = Attachment(
    filename = 'text.txt',
    content = attach_content,
    charset = "utf-8",
    mimetype = "text/plain",
    )


attach_content = u"""<html><head><meta http-equiv="Content-Type" content="text/html;charset=utf-8" /></head>
<body>
    <p>Text file attachment</p>
    <p>Just to test if it works</p>
    <p>Русский язык должен быть в правильной кодирове</p>
</body>"""
attach_content = attach_content.encode('utf-8')

html_attachment = Attachment(
    filename = 'text2.html',
    content = attach_content,
    charset = "utf-8",
    mimetype = "text/html",
    )


email = Email(
    rcpt = 'highcatland@gmail.com',
    subject = 'Emailer test',
    reply_to = 'HighCat <highcatland@gmail.com>',
    body = u'<html><body><h1>Test email</h1><p>Some text in paragraph</p><p>Attachment should exist - please check.</p><p>Юникодный текст (unicode text here).</p></body></html>',
    mimetype = 'text/html',
    attachments = [txt_attachment, html_attachment],
    )


account.send(email)
