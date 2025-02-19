import re
import random
import sys
import pdfplumber
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init(autoreset=True)


def load_words_from_file(filename):
    """从文件中加载单词，返回单词集合（大小写敏感）"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def load_cet4_words(filename):
    """加载四级词汇文件，返回单词集合（大小写敏感）"""
    return load_words_from_file(filename)


def read_practice_text(filename):
    """读取练习文本并分割成句子（支持中英文标点），支持 PDF 和 EPUB 文件"""
    if filename.endswith('.pdf'):
        text = read_pdf(filename)
    elif filename.endswith('.epub'):
        text = read_epub(filename)
    else:
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    # 预处理文本
    text = preprocess_text(text)
    # 分句
    sentences = split_sentences(text)
    # 过滤无效句子
    sentences = [s for s in sentences if len(s) > 1]
    return sentences


def read_pdf(filename):
    """使用pdfplumber读取 PDF 文件内容"""
    text = ""
    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text


def read_epub(filename):
    """使用ebooklib和BeautifulSoup读取 EPUB 文件内容"""
    book = epub.read_epub(filename)
    text = ""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode('utf-8')
        soup = BeautifulSoup(content, 'html.parser')
        text += soup.get_text()
    return text


def preprocess_text(text):
    """预处理文本，去除多余空格、换行符，合并断词"""
    # 合并断词
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    # 去除多余空格和换行符
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_sentences(text):
    """优化的分句正则表达式"""
    pattern = r'(?<=[.!?。！？])\s*(?=[^.!?。！？])'
    sentences = re.split(pattern, text)
    return sentences


def process_sentence(sentence, four_words=None, high_freq_words=None, practiced_words=None):
    """改进版处理函数，支持中文和英文词汇处理"""
    # 识别中文和英文词汇
    tokens = re.findall(r'([\u4e00-\u9fff]+|[a-zA-Z]+)([^\u4e00-\u9fff^a-zA-Z]*)', sentence)
    if not tokens:
        return None

    # 第一优先级：属于四级词汇且非高频词且未练习过
    if four_words and high_freq_words and practiced_words:
        primary_candidates = [
            i for i, (core, _) in enumerate(tokens)
            if core in four_words and core.lower() in {w.lower() for w in four_words}
            and core.lower() not in high_freq_words and core.lower() not in practiced_words
        ]
    else:
        primary_candidates = []

    # 第二优先级：非高频词且未练习过（不论是否四级）
    if high_freq_words and practiced_words:
        secondary_candidates = [
            i for i, (core, _) in enumerate(tokens)
            if core.lower() not in high_freq_words and core.lower() not in practiced_words
        ]
    else:
        secondary_candidates = []

    # 选择策略
    if primary_candidates:
        chosen = random.choice(primary_candidates)
    elif secondary_candidates:
        chosen = random.choice(secondary_candidates)
    else:
        chosen = random.randint(0, len(tokens) - 1)

    correct_answer = tokens[chosen][0]
    modified = [
        '_____' + suffix if i == chosen else core + suffix
        for i, (core, suffix) in enumerate(tokens)
    ]

    return ''.join(modified), correct_answer


def record_practiced_word(word, filename):
    """将练习过的单词记录到文件中"""
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(word + '\n')


def save_progress(progress, filename):
    """保存当前练习的句子索引"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(str(progress))


def load_progress(filename):
    """加载上次练习的句子索引"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def main():
    # 定义默认练习文件
    default_practice_file = 'default_practice.txt'

    # 如果用户没有指定任何练习文件，则使用默认练习文件
    if len(sys.argv) < 2:
        practice_text_file = default_practice_file
    elif len(sys.argv) > 4:
        print("使用方法: python typing_train.py [练习文本文件] [四级词汇文件（可选）] [高频词文件（可选）]")
        return
    else:
        practice_text_file = sys.argv[1]

    # 加载文件
    sentences = read_practice_text(practice_text_file)

    four_words = set()
    high_freq_words = set()
    practiced_words = set()
    practiced_words_file = 'practiced_words.txt'

    if len(sys.argv) >= 3:
        four_words = load_cet4_words(sys.argv[2])
    if len(sys.argv) == 4:
        high_freq_words = load_words_from_file(sys.argv[3])

    try:
        # 尝试加载已练习过的词汇文件
        practiced_words = load_words_from_file(practiced_words_file)
    except FileNotFoundError:
        pass

    # 加载上次练习的进度
    progress_file = f'{practice_text_file}.progress'
    start_index = load_progress(progress_file)

    prev_sentence = None
    prev_answer = None
    current_index = start_index
    # 处理每个句子
    while current_index < len(sentences):
        sent = sentences[current_index]
        processed = process_sentence(sent, four_words, high_freq_words, practiced_words)
        if not processed:
            current_index += 1
            continue

        modified, answer = processed

        # 交互环节
        while True:
            print(f"\n=== {current_index + 1}/{len(sentences)} ===")
            print(modified)

            user_input = input(": ").strip()
            if user_input.lower() == 'q':
                # 保存当前进度
                save_progress(current_index, progress_file)
                print("\n练习已终止")
                return
            elif user_input.lower() == 'p':
                if prev_sentence and prev_answer:
                    print(f"\n上一句: {prev_sentence.replace('_____', prev_answer)}")
                    print(f"缺失单词: {prev_answer}\n")
                else:
                    print("还没有上一句哦。\n")
            elif user_input.lower() == 'g':
                try:
                    target_index = int(input("请输入要跳转的句子编号（1 - {}）: ".format(len(sentences)))) - 1
                    if 0 <= target_index < len(sentences):
                        current_index = target_index
                        break
                    else:
                        print("输入的句子编号超出范围，请重新输入。")
                except ValueError:
                    print("输入无效，请输入一个有效的数字。")
            elif user_input == answer:
                full_correct_sentence = modified.replace('_____', answer)
                print(Fore.GREEN + f"{full_correct_sentence}\n" + Style.RESET_ALL)
                # 记录练习过的单词
                record_practiced_word(answer, practiced_words_file)
                practiced_words.add(answer)
                # 保存当前进度
                save_progress(current_index + 1, progress_file)
                prev_sentence = modified
                prev_answer = answer
                current_index += 1
                break
            else:
                print(Fore.RED + f"{answer}\n" + Style.RESET_ALL)


if __name__ == "__main__":
    main()
