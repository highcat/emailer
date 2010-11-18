__all__ = ['Account', 'Email', 'Attachment']

import datetime, time
from email.mime.multipart import MIMEBase, MIMEMultipart
from email.header import Header
from email.charset import Charset, QP
from email.encoders import encode_quopri, encode_base64
from mimetypes import guess_type
from smtplib import SMTP, SMTP_SSL

def is7bit(s):
    for c in s:
        if ord(c) > 127:
            return False
    return True

class Account(object):
    def __init__(self, email, fromname, server, login=None, password=None, port=25, ssl=False):
        self.email = email
        self.fromname = fromname
        self.server = server
        self.port = port
        self.login = login
        self.password = password
        self.ssl = ssl

    def send(self, emails):
        if isinstance(emails, Email):
            emails = [emails]
        if len([e for e in emails if e.__class__ != Email]):
            raise TypeError('emails must be Email or list of Email instances')

        smtpclass = SMTP_SSL if self.ssl else SMTP
        if self.server == 'localhost':
            smtp = smtpclass(self.server)
        else:
            smtp = smtpclass(self.server, self.port)
        if self.login and self.password:
            smtp.login(self.login, self.password)
        for email in emails:
            print "(%s) %s" % (type(email.subject), email.subject)
            c = Charset(email.charset)
            c.header_encoding = QP
            c.body_encoding = 0
            r = Charset(email.charset)
            r.header_encoding = 0
            r.body_encoding = 0

            email.normalize_email_list('rcpt')
            email.normalize_email_list('cc')
            mime1, mime2 = email.mimetype.split('/')
            mainpart = MIMEBase(mime1, mime2)
            if not email.force_7bit:
                mainpart.set_param('charset', email.charset)

            if len(email.attachments):
                message = MIMEMultipart(
                            'related' if len(email.attachments) else 'mixed')
                message.attach(mainpart)
                del mainpart['mime-version']
            else:
                message = mainpart

            message['Date'] = datetime.datetime.now().strftime(
                '%a, %d %b %Y %H:%M:%S') + (" +%04d" % (time.timezone/-36,))

            h = Header()
            fromname = self.fromname.encode(email.charset, 'xmlcharrefreplace')
            h.append(fromname, r if is7bit(fromname) else c)
            h.append('<%s>' % self.email, r)
            message['From'] = h

            message['To'] = email.get_emails_header('rcpt')
            if len(email.cc):
                message['CC'] = email.get_emails_header('cc')

            subject = email.subject.encode(email.charset, 'xmlcharrefreplace')
            print "(%s) %s" % (type(subject), subject)
            message['Subject'] = Header(subject, r if is7bit(subject) else c)

            if email.force_7bit:
                body = email.body.encode('ascii', 'xmlcharrefreplace')
            else:
                body = email.body.encode(email.charset, 'xmlcharrefreplace')
            mainpart.set_payload(body)

            if is7bit(body):
                mainpart['Content-Transfer-Encoding'] = '7bit'
            else:
                encode_quopri(mainpart)

            for attachment in email.attachments:
                if attachment.__class__ != Attachment:
                    raise TypeError("invalid attachment")

                mimetype = attachment.mimetype
                if not mimetype:
                    mimetype, encoding = guess_type(attachment.filename)
                    if not mimetype:
                        mimetype = 'application/octet-stream'
                mime1, mime2 = mimetype.split('/')
                part = MIMEBase(mime1, mime2)
                part.set_param('name', attachment.filename)

                del part['mime-version']

                if attachment.id:
                    part['Content-Disposition'] = 'inline'
                else:
                    part['Content-Disposition'] = 'attachment'
                part.set_param('filename', attachment.filename,
                                                'Content-Disposition')

                if attachment.id:
                    part['Content-ID'] = '<%s>' % attachment.id

                part.set_payload(attachment.content)
                encode_base64(part)

                message.attach(part)

            smtp.sendmail(self.email, [rcpt[1] for rcpt in email.rcpt] +
                            [cc[1] for cc in email.cc], message.as_string())

        smtp.quit()

class Email(object):
    def __init__(self, rcpt, subject, body, mimetype='text/plain', cc=[], attachments=[], charset='utf-8', force_7bit=False):
        self.rcpt = rcpt
        self.cc = cc
        self.subject = subject
        self.body = body
        self.mimetype = mimetype
        self.attachments = attachments
        self.force_7bit = force_7bit
        self.charset = charset

    def normalize_email_list(self, attr):
        emails = self.__getattribute__(attr)
        if type(emails) != list:
            emails = [emails]
        for i in range(len(emails)):
            if type(emails[i]) == tuple:
                if (type(emails[i][0]) not in (str, unicode)) or \
                    (type(emails[i][1]) not in (str, unicode)):
                        return TypeError('invalid "%s"' % attr)
            else:
                if type(emails[i]) not in (str, unicode):
                    return TypeError('invalid "%s"' % attr)
                emails[i] = (None, emails[i])
        self.__setattr__(attr, emails)

    def get_emails_header(self, attr):
        c = Charset(self.charset)
        c.header_encoding = QP
        c.body_encoding = 0
        r = Charset(self.charset)
        r.header_encoding = 0
        r.body_encoding = 0

        h = Header()
        self.normalize_email_list(attr)
        emails = self.__getattribute__(attr)

        for i in range(len(emails)):
            name, email = emails[i]

            if i:
                h.append(',', r)

            if name:
                name = name.encode(self.charset, 'xmlcharrefreplace')
                h.append(name, r if is7bit(name) else c)
                h.append('<%s>' % email, r)
            else:
                h.append(email, r)

        return h

class Attachment(object):
    def __init__(self, filename, content, id=None, mimetype=None):
        self.filename = filename
        self.content = content
        self.mimetype = mimetype
        self.id = id

