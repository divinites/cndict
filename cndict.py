import sublime_plugin
import sublime
import urllib.request
import urllib.error
from threading import Thread
from urllib.parse import quote
import json
import mdpopups


_YOUDAO_API = "http://fanyi.youdao.com/openapi.do?keyfrom=divinites&key=1583185521&type=data&doctype=json&version=1.1&q="
_CIBA_API = "http://dict-co.iciba.com/api/dictionary.php?w="


class CndictCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        if 'dict' in kwargs.keys():
            self.args = kwargs['dict']
        window = self.window
        view = window.active_view()
        window.run_command("find_under_expand")
        sel = view.sel()
        region = sel[0]
        word = view.substr(region)
        func = LookUpDict(window, word, self.args)
        func.start()


class EraseDictCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.window.active_view().erase_phantoms('trans')


class LookUpDict(Thread):
    def __init__(self, window, word, args):
        Thread.__init__(self)
        self.window = window
        self.view = self.window.active_view()
        self.word = word
        self.args = args

    def checkword(self, word):
        if self.word == '':
            return False
        else:
            return True

    def acquiredata(self, word):
        if self.args == 'Youdao':
            request = _YOUDAO_API + quote(self.word)
        elif self.args == 'Jinshan':
            request = _CIBA_API + quote(
                self.word) + "&type=json&key=0EAE08A016D6688F64AB3EBB2337BFB0"
        else:
            print("Invalid dictionary!")
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.URLError:
            raise Exception(u'网速不给力还是怎么回事，再试试？')

        data = response.read().decode('utf-8')
        return (json.loads(data))

    def format(self, json_data):
        snippet = ''
        if self.args == 'Youdao':
            if 'basic' in json_data:
                for explain in json_data['basic'].items():
                    if explain[0] == 'explains':
                        for i in explain[1:]:
                            snippet += '\n'.join(i)
                snippet += "\n------------------------\n"
            if "web" in json_data:
                for explain in json_data['web']:
                    net_explain = ','.join(explain['value'])
                    snippet += "{} : {}\n".format(explain['key'], net_explain)
        elif self.args == 'Jinshan':
            if 'symbols' in json_data:
                for explain in json_data['symbols'][0]['parts']:
                    if isinstance(explain['means'][0], str):
                        snippet += '{} : {}\n'.format(
                            explain["part"], ','.join(explain["means"]))
                    if isinstance(explain['means'][0], dict):
                        for i in explain['means']:
                            snippet += '{}:{}\n'.format("释义", i["word_mean"])
                snippet += "\n------------------------\n"
        else:
            snippet += "可能太长了……词典里没有"
        return snippet

    def on_close_phantom(self, href):
        """Close all phantoms."""
        mdpopups.erase_phantoms(self.view, 'trans')

    def run(self):
        if self.checkword(self.word):
            json_data = self.acquiredata(self.word)
            snippet = self.format(json_data)
        else:
            snippet = "忘记选字了吧？"
        close = '[Close/关闭\n](#)'
        settings = sublime.load_settings("cndict.sublime-settings")
        if settings.get("phantom", True):
            mdpopups.add_phantom(view=self.view,
                                 key="trans",
                                 region=self.view.sel()[0],
                                 content=snippet + close,
                                 layout=sublime.LAYOUT_BELOW,
                                 on_navigate=self.on_close_phantom,
                                 md=True)
        else:
            board = self.window.create_output_panel("trans")
            board.run_command('append', {'characters': snippet})
            self.window.run_command("show_panel", {"panel": "output.trans"})
