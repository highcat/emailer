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


email = Email(
    rcpt = 'highcatland@gmail.com',
    subject = 'Emailer test',
    reply_to = 'HighCat <highcatland@gmail.com>',
    body = '<html><body><h1>Test email</h1><p>Some text in paragraph</p><p>Attachment should exist - please check.</p></body></html>',
    mimetype = 'text/html',
    attachments = [txt_attachment],
    )


account.send(email)
