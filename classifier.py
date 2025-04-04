import json
import os
import re
from typing import List
from transformers import pipeline

# Нові мітки (тільки токсичні категорії, без Safe)
LABELS = [
    "Hate speech or harassment",
    "Propaganda or ideological harm",
    "Exploitation or abuse",
    "Self-harm or suicide"
]

class TextClassifier:
    def __init__(self,
                 model_name="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",  # Краща модель для NLI
                 device=0,  # 0 для GPU
                 threshold=0.5,  # Зменшений поріг для чутливості
                 batch_size=8):
        
        self.pipeline = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=device,
            hypothesis_template="This message contains {}."  # Явний шаблон
        )
        self.threshold = threshold
        self.batch_size = batch_size
        self.cache = {}
        self.cache_path = "classification_cache.json"

        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"⚠️ Не вдалося завантажити кеш: {e}")

    def classify(self, texts: List[str]) -> List[dict]:
        # Фільтрація текстів
        original_texts = []
        for t in texts:
            if not t or not t.strip():
                continue
            clean_t = t.strip()
            low_t = clean_t.lower()
            if low_t in ["[media]", "[photo]", "[video]"]:
                continue
            if len(clean_t) < 3 or clean_t.isdigit():
                continue
            if re.fullmatch(r'(.)\1{2,}', clean_t):
                continue
            original_texts.append(clean_t)

        if not original_texts:
            print("❌ Немає текстів для класифікації після фільтрації.")
            return []

        results = [None] * len(original_texts)
        to_classify_texts = []
        to_classify_indices = {}
        cached_count = 0

        for idx, text in enumerate(original_texts):
            if text in self.cache:
                cached = self.cache[text]
                results[idx] = {"text": text, "labels": cached["labels"], "scores": cached["scores"]}
                cached_count += 1
            else:
                if text not in to_classify_indices:
                    to_classify_indices[text] = []
                    to_classify_texts.append(text)
                to_classify_indices[text].append(idx)

        if to_classify_texts:
            try:
                from tqdm import tqdm
            except ImportError:
                tqdm = None

            if tqdm:
                pbar = tqdm(total=len(original_texts), desc="🧠 Класифікація", unit="msg")
                pbar.update(cached_count)

            for i in range(0, len(to_classify_texts), self.batch_size):
                batch_texts = to_classify_texts[i:i + self.batch_size]
                batch_results = self.pipeline(
                    batch_texts,
                    candidate_labels=LABELS,
                    multi_label=True
                )

                if not isinstance(batch_results, list):
                    batch_results = [batch_results]

                for txt, result in zip(batch_texts, batch_results):
                    filtered_labels = []
                    filtered_scores = []

                    for label, score in zip(result["labels"], result["scores"]):
                        if score >= self.threshold:
                            filtered_labels.append(label)
                            filtered_scores.append(score)

                    # Якщо жодна токсична категорія не знайдена — вважаємо повідомлення безпечним
                    if not filtered_labels:
                        filtered_labels = ["Safe"]
                        filtered_scores = [1.0]

                    for idx in to_classify_indices.get(txt, []):
                        results[idx] = {"text": txt, "labels": filtered_labels, "scores": filtered_scores}
                    self.cache[txt] = {"labels": filtered_labels, "scores": filtered_scores}

                if tqdm:
                    pbar.update(len(batch_texts))

            if tqdm:
                pbar.close()

        # Зберігаємо кеш
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Помилка збереження кешу: {e}")

        return results
