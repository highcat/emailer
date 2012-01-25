__all__ = ['Account', 'Email', 'Attachment']

import datetime, time
from email.mime.multipart import MIMEBase, MIMEMultipart
from email.header import Header
from email.charset import Charset, QP
from email.encoders import encode_quopri, encode_base64
from email.parser import Parser
from mimetypes import guess_type
from smtplib import SMTP, SMTP_SSL
from poplib import POP3_SSL, POP3

def is7bit(s):
    for c in s:
        if ord(c) > 127:
            return False
    return True

class Account(object):
    def __init__(self, email, fromname, server, popserver = None, login=None, password=None, port=25, ssl=False):
        self.email = email
        self.fromname = fromname
        self.server = server
        self.popserver = popserver
        self.port = port
        self.login = login
        self.password = password
        self.ssl = ssl
        self.__pop = None
    
    def __pop_connect(self):
        self.__pop = globals().get('POP3' + ('_SSL' if self.ssl else ''))(self.popserver)
        self.__pop.user(self.login)
        self.__pop.pass_(self.password)

    def stat(self):
        if not self.__pop:
            self.__pop_connect()
        return self.__pop.stat()

    def retr(self, n):
        if not self.__pop:
            self.__pop_connect()
        p = Parser()
        return p.parsestr('\r\n'.join(self.__pop.retr(n)[1]))

    def dele(self, n):
        if not self.__pop:
            self.__pop_connect()
        return self.__pop.dele(n)

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
            c = Charset(email.charset)
            c.header_encoding = QP
            c.body_encoding = 0
            r = Charset(email.charset)
            r.header_encoding = 0
            r.body_encoding = 0

            email.normalize_email_list('rcpt')
            email.normalize_email_list('cc')
            email.normalize_email_list('bcc')
            mime1, mime2 = email.mimetype.split('/')
            mainpart = MIMEBase(mime1, mime2)
            if not email.force_7bit:
                mainpart.set_param('charset', email.charset)

            if len(email.attachments):
                message = MIMEMultipart('mixed')
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
            if len(email.bcc):
                message['BCC'] = email.get_emails_header('bcc')

            subject = email.subject.encode(email.charset, 'xmlcharrefreplace')
            message['Subject'] = Header(subject, r if is7bit(subject) else c)

            if email.reply_to:
                message['Reply-To'] = email.get_emails_header('reply_to')

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

                # using newer rfc2231 (not supported by Outlook):
                # part.set_param('name', attachment.filename.encode('utf-8'), charset = 'utf-8')

                # hack: using deprecated rfc2047 - supported by Outlook:
                part.set_param('name', str(Header(attachment.filename)))
                del part['mime-version']

                if attachment.id:
                    part['Content-Disposition'] = 'inline'
                else:
                    part['Content-Disposition'] = 'attachment'

                # using newer rfc2231 (not supported by Outlook):
                # part.set_param('filename',
                #                attachment.filename.encode('utf-8'),
                #                'Content-Disposition',
                #                charset = 'utf-8')

                # hack: using deprecated rfc2047 - supported by Outlook:
                part.set_param('filename',
                               str(Header(attachment.filename)),
                               'Content-Disposition')

                if attachment.id:
                    part['Content-ID'] = '<%s>' % attachment.id

                if attachment.charset:
                    part.set_charset(attachment.charset)

                part.set_payload(attachment.content)
                encode_base64(part)

                message.attach(part)

            smtp.sendmail(self.email, [rcpt[1] for rcpt in email.rcpt] +
                          [cc[1] for cc in email.cc] +
                          [bcc[1] for bcc in email.bcc], message.as_string())

        smtp.quit()

class Email(object):
    def __init__(self, rcpt, subject, body, mimetype='text/plain', cc=[], bcc=[], reply_to=None, attachments=[], charset='utf-8', force_7bit=False):
        self.rcpt = rcpt
        self.subject = subject
        self.body = body
        self.mimetype = mimetype
        self.cc = cc
        self.bcc = bcc
        self.reply_to = reply_to
        self.attachments = attachments
        self.charset = charset
        self.force_7bit = force_7bit

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
    def __init__(self, filename, content, id=None, mimetype=None, charset=None):
        self.filename = filename if isinstance(filename, unicode) else unicode(filename)
        self.content = content
        self.mimetype = mimetype
        self.charset = charset
        self.id = id

