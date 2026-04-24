import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

def count_sentences(text):
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    return len(sentences)

def tokenize_words(text):
    return re.findall(r'\b[a-zA-Z]+\b', text.lower())

def load_word_list(filepath):
    words = set()
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            word = line.strip().lower()
            if word and not word.startswith(';'):
                words.add(word)
    return words

def load_stopword_folder(folder_path):
    stop_words = set()
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.txt'):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    word = line.strip().lower()
                    if word:
                        stop_words.add(word)
    return stop_words


positive_words = load_word_list('positive-words.txt')
negative_words = load_word_list('negative-words.txt')

STOP_WORDS = load_stopword_folder('stopwords_all')
print(f"Total stop words loaded: {len(STOP_WORDS)}")


def extract_article_text(url):
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove noisy elements
    for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
        tag.decompose()
    title = soup.title.string.strip() if soup.title else ''
    article = soup.find('article')

    if article:
        text = article.get_text(separator=' ')
    else:
        paragraphs = soup.find_all('p')
        text = ' '.join(p.get_text() for p in paragraphs)

    return title, text.strip()


def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def count_syllables(word):
    vowels = "aeiouy"
    count = 0
    prev_char_was_vowel = False

    for char in word:
        if char in vowels:
            if not prev_char_was_vowel:
                count += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False

    if word.endswith("e"):
        count = max(1, count - 1)

    return count if count > 0 else 1


def count_personal_pronouns(text):
    pattern = r'\b(i|we|my|ours|us)\b'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return len(matches)


def analyze_text(text):
    cleaned = clean_text(text)
    words = tokenize_words(cleaned)

    # remove stopwords
    words = [w for w in words if w not in STOP_WORDS]

    word_count = len(words)
    sentence_count = count_sentences(text)

    positive_score = sum(1 for w in words if w in positive_words)
    negative_score = sum(1 for w in words if w in negative_words)

    polarity_score = (positive_score - negative_score) / ((positive_score + negative_score) + 1e-6)
    subjectivity_score = (positive_score + negative_score) / (word_count + 1e-6)

    syllable_counts = [count_syllables(w) for w in words]
    complex_words = [w for w, s in zip(words, syllable_counts) if s > 2]

    avg_sentence_length = word_count / (sentence_count + 1e-6)
    percentage_complex_words = len(complex_words) / (word_count + 1e-6)
    fog_index = 0.4 * (avg_sentence_length + percentage_complex_words)

    avg_words_per_sentence = avg_sentence_length
    complex_word_count = len(complex_words)
    syllables_per_word = sum(syllable_counts) / (word_count + 1e-6)
    personal_pronouns = count_personal_pronouns(text)
    avg_word_length = sum(len(w) for w in words) / (word_count + 1e-6)

    return {
        'POSITIVE SCORE': positive_score,
        'NEGATIVE SCORE': negative_score,
        'POLARITY SCORE': polarity_score,
        'SUBJECTIVITY SCORE': subjectivity_score,
        'AVG SENTENCE LENGTH': avg_sentence_length,
        'PERCENTAGE OF COMPLEX WORDS': percentage_complex_words,
        'FOG INDEX': fog_index,
        'AVG NUMBER OF WORDS PER SENTENCE': avg_words_per_sentence,
        'COMPLEX WORD COUNT': complex_word_count,
        'WORD COUNT': word_count,
        'SYLLABLE PER WORD': syllables_per_word,
        'PERSONAL PRONOUNS': personal_pronouns,
        'AVG WORD LENGTH': avg_word_length
    }



def main():
    input_df = pd.read_excel('Input.xlsx')

    os.makedirs('extracted_articles', exist_ok=True)
    results = []

    for _, row in input_df.iterrows():
        url_id = row['URL_ID']
        url = row['URL']

        try:
            title, article_text = extract_article_text(url)

            with open(f'extracted_articles/{url_id}.txt', 'w', encoding='utf-8') as f:
                f.write(title + '\n\n' + article_text)

            metrics = analyze_text(article_text)

            row_data = row.to_dict()
            row_data.update(metrics)
            results.append(row_data)

            print(f"Processed {url_id}")

        except Exception as e:
            print(f"Error processing {url_id}: {e}")

    output_df = pd.DataFrame(results)
    output_df.to_excel('Output Data Structure.xlsx', index=False)


if __name__ == "__main__":
    main()


