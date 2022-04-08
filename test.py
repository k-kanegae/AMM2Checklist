#必要に応じて下記のLibraryをInstall
#pip install pdfminer.six
#pip install streamlit

import pdfminer
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
import re 
import streamlit as st
from pathlib import Path
import tempfile
import os

st.set_page_config(layout="wide")
st.title("AMMチェックリスト")



def gettext(pdfname,pagenos):
    # PDFファイル名が未指定の場合は、空文字列を返して終了
    if (pdfname == ''):
        return ''
    else:
        # 処理するPDFファイルを開く/開けなければ
        try:
            fp = open(pdfname, 'rb')
        except:
            return ''
        
    # リソースマネージャインスタンス
    rsrcmgr = PDFResourceManager()
    # 出力先インスタンス
    outfp = StringIO()
    # パラメータインスタンス
    laparams = LAParams()
    laparams.boxes_flow = None          # -1.0（水平位置のみが重要）から+1.0（垂直位置のみが重要）default 0.5
    laparams.line_overlap = -10       #上下が重なっている場合に同一列に入れる基準。あまり関係なかった。
    laparams.word_margin = 500        # default 0.1
    laparams.char_margin = 500        # default 2.0
    laparams.line_margin = 10           # default 0.5
    # デバイスの初期化
    device = TextConverter(rsrcmgr, outfp, codec='utf-8', laparams=laparams)
    # テキスト抽出インタプリタインスタンス
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # 対象ページを読み、テキスト抽出する。（maxpages：0は全ページ）
    for page in PDFPage.get_pages(fp, pagenos=pagenos, maxpages=None, password=None,caching=True, check_extractable=True):
        interpreter.process_page(page)
    #取得したテキストをすべて読みだす
    ret = outfp.getvalue()
    # 後始末をしておく    
    fp.close()
    device.close()
    outfp.close()
    # 空白と改行をとりさり一塊のテキストとして返す ⇔これは使うのでCNL。
    return ret

def make_checklist(uf, pn):
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file: #uploaded_fileそのままでは使えないのでtmp fileを作成してそこに書き込む形で読み込む。
        fp = Path(tmp_file.name) #tmp fileの場所を取得する
        fp.write_bytes(uf.getvalue()) #tmp fileの中身をuploaded_fileで上書きする。
        ret = gettext(fp, pn) #tmp file pathを使ってテキスト抽出する。
        ret = re.sub("\x0c","",ret) #なぜか入っている場所があるので消去。
        ret = re.sub("Selected Customer.+(Page \d{1,} of \d{1,})","\\1",ret) #フッターをPage数のみに変更
        ret = re.sub("(Printed by.+\n)|(777 – AMM.+\n)|(DO NOT KEEP.\n)|(Rev.+\d{4,}\n)|(TASK.+\d{4,}\n)|(EFFECTIVITY.+\n)","",ret) #ヘッダー削除。行跨ぎで削除しようとするとうまくいかないので、1行ずつ判別して削除。
        ret = re.sub("( \n){2,}","",ret) #ページ区切りで大量に入る空白＋改行を削除する。
        ret = re.sub(",\n",",",ret) #EFF Codeで入る改行を削除する。IPC REFで入ってくる。
        ret = re.sub("([A-Z]\.  )","\n\\1",ret) #見やすくするため、A. B. C.のような大項目前で改行を入れる。
        ret = re.sub("([A-Z][a-z])"," \\1",ret) #大文字1つ＋小文字1つ（通常の単語）前に空白を入れて見やすくする。CB LOCのようなところで使う。
        ret_split = re.split("(?=[A-Z]\.  )|(?=SUBTASK)",ret) #大項目かSUBTASKで分割する。分割個所にチェックボックスを入れる。 
    with open("test.txt","w", encoding='UTF-8', errors='ignore') as f:
        f.write(ret)
    return ret_split

uploaded_file = st.sidebar.file_uploader("AMMのPDF FileをこちらにUploadしてください",type="pdf")
start_page = st.sidebar.number_input("AMM本文の最初のページ番号(BULLと図面除く)",1,None,1)
fin_page = st.sidebar.number_input("AMM本文の最終ページ番号(BULLと図面除く)",1,None,1) 

if uploaded_file is not None and start_page is not None and fin_page is not None:
    
    if start_page == fin_page:
        pagenos=[]
        pagenos.append(start_page-1) #1ページだけだとRangeがうまく働かないのでこうした。
    else:
        pagenos = list(range(start_page-1, fin_page)) #pagenosはリスト形式にする必要がある。Pageはゼロ始まりなのでStartは-1, Rangeの終点はPythonの仕様上-1になるのでそのまま。
    
    if st.sidebar.checkbox("チェックリスト作成"): #これをボタンにすると、本文のチェックボックスを1つでも入れると全Resetになってしまう。ボタンの状態がTRUEからFALSEに切り替わるため。そのため、状態保持できるCheckboxにした。
        ret_splits = make_checklist(uploaded_file, pagenos)
        i = 1
        for split in ret_splits:
            split = re.sub("\n","  \n",split)
            st.write('<span style="color:red;background:pink">・・・・・・・・・・・・・・・・・・・・・・・・・・・・・</span>',unsafe_allow_html=True)
            st.checkbox('以下の手順を確認もしくは終了したらチェックしてください。', key=i) #LoopでWidgetを作るとKeyが重複してエラーになるので、KeyをMAN指定する必要あり。
            st.text(split)
            i += 1
        

