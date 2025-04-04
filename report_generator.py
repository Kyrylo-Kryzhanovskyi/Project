# report_generator.py 
import json
import os
from collections import Counter, defaultdict
import matplotlib.pyplot as plt


def load_classification_results(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_dir_name(filepath):
    base = os.path.basename(filepath)
    name = os.path.splitext(base)[0].replace("classified_", "")
    return name.replace(" ", "_").replace("/", "_").replace("\\", "_")


def create_output_folder(base_folder, name):
    path = os.path.join(base_folder, name)
    os.makedirs(path, exist_ok=True)
    return path


def summarize_classification(results):
    label_counter = Counter()
    multi_label_counts = defaultdict(int)
    scores_per_label = defaultdict(list)
    lengths_per_label = defaultdict(list)

    for entry in results:
        text = entry['text']
        text_len = len(text)
        labels = entry['labels']
        scores = entry['scores']

        if len(labels) == 1 and labels[0].startswith("Safe"):
            label_counter['Safe'] += 1
            scores_per_label['Safe'].append(1.0)
            lengths_per_label['Safe'].append(text_len)
        else:
            multi_label_counts[len(labels)] += 1
            for label, score in zip(labels, scores):
                label_counter[label] += 1
                scores_per_label[label].append(score)
                lengths_per_label[label].append(text_len)

    return label_counter, multi_label_counts, scores_per_label, lengths_per_label


def print_summary(label_counter, multi_label_counts, scores_per_label, lengths_per_label, output_path):
    total = sum(label_counter.values())
    lines = []
    lines.append(f"📊 Загальна кількість класифікованих повідомлень: {total}\n")
    lines.append("📌 Кількість повідомлень за категоріями:")
    for label, count in label_counter.most_common():
        percent = count / total * 100
        avg_score = sum(scores_per_label[label]) / len(scores_per_label[label]) if scores_per_label[label] else 0
        avg_len = sum(lengths_per_label[label]) / len(lengths_per_label[label]) if lengths_per_label[label] else 0
        lines.append(f"- {label}: {count} ({percent:.1f}%) | Avg score: {avg_score:.2f} | Avg length: {avg_len:.0f} chars")

    # Кількість повідомлень з кількома мітками
    lines.append("\n📌 Кількість повідомлень з кількома мітками:")
    
    multi_labels_only = {k: v for k, v in multi_label_counts.items() if k > 1}
    if not multi_labels_only:
        lines.append("   Немає повідомлень з кількома мітками")
    else:
        for k in sorted(multi_labels_only):
            lines.append(f"- {k} labels: {multi_labels_only[k]}")

    with open(os.path.join(output_path, "classification_summary.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print("\n".join(lines))


def show_top_examples(results, output_path, top_n=5, threshold_low=0.4, threshold_high=0.7):
    lines = []
    lines.append("🔍 Найбільш \"сумнівні\" повідомлення (мітки з низькою впевненістю):")
    count = 0
    for entry in results:
        for label, score in zip(entry['labels'], entry['scores']):
            if not label.startswith("Safe") and threshold_low <= score <= threshold_high:
                lines.append(f"\n📝 Text: {entry['text'][:300]}...")
                lines.append(f"🔸 Label: {label}, Score: {score:.2f}")
                count += 1
                if count >= top_n:
                    break
        if count >= top_n:
            break

    with open(os.path.join(output_path, "top_uncertain_examples.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def show_top_toxic(results, output_path, top_n=5):
    scored = []
    for entry in results:
        if "Safe" in entry['labels'] and len(entry['labels']) == 1:
            continue
        toxicity_score = sum([s for l, s in zip(entry['labels'], entry['scores']) if not l.startswith("Safe")])
        scored.append((toxicity_score, entry))

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:top_n]

    lines = ["🔥 Топ найтоксичніших повідомлень:"]
    if len(top) == 0:
        lines.append("❌ Токсичних повідомлень не знайдено")
    else:
        for score, entry in top:
            lines.append(f"\n📝 Text: {entry['text'][:300]}...")
            lines.append(f"🔸 Total toxicity score: {score:.2f}")
            for label, s in zip(entry['labels'], entry['scores']):
                lines.append(f"   - {label}: {s:.2f}")

    with open(os.path.join(output_path, "top_toxic_messages.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def save_per_category(results, output_path):
    per_category = defaultdict(list)
    for entry in results:
        for label in entry['labels']:
            per_category[label].append(entry)

    for label, entries in per_category.items():
        filename = f"category_{label.replace(' ', '_').replace('/', '_')}.json"
        with open(os.path.join(output_path, filename), 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)


def save_bar_chart(label_counter, output_path):
    labels = list(label_counter.keys())
    counts = [label_counter[l] for l in labels]

    plt.figure(figsize=(10, 6))
    plt.barh(labels, counts)
    plt.xlabel("Кількість повідомлень")
    plt.title("Розподіл класифікації по категоріях")
    plt.tight_layout()
    plt.savefig(os.path.join(output_path, "chart.png"))
    plt.close()


def main():
    path = input("📁 Введіть шлях до JSON з класифікацією: ").strip()
    if not os.path.exists(path):
        print("❌ Файл не знайдено!")
        return

    results = load_classification_results(path)
    name = safe_dir_name(path)
    output_path = create_output_folder("reports", name)

    label_counter, multi_label_counts, scores_per_label, lengths_per_label = summarize_classification(results)
    print_summary(label_counter, multi_label_counts, scores_per_label, lengths_per_label, output_path)
    show_top_examples(results, output_path)
    show_top_toxic(results, output_path)
    save_per_category(results, output_path)
    save_bar_chart(label_counter, output_path)

    print(f"\n✅ Звіт збережено у папці: {output_path}")


if __name__ == "__main__":
    main()
