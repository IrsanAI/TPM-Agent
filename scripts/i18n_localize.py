#!/usr/bin/env python3
"""Apply deterministic phrase-based localization patches to i18n READMEs.

This script is intentionally conservative:
- It only replaces known canonical English lines/phrases.
- It preserves commands/code fences/paths.
- It can be rerun safely (idempotent replacements).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "docs" / "i18n"

COMMON = {
    "- **Gate 1 – Environment:** Python/platform context is correct (`env`).": {
        "es": "- **Gate 1 – Entorno:** el contexto Python/plataforma es correcto (`env`).",
        "it": "- **Gate 1 – Ambiente:** il contesto Python/piattaforma è corretto (`env`).",
        "fr": "- **Gate 1 – Environnement :** le contexte Python/plateforme est correct (`env`).",
        "pt-BR": "- **Gate 1 – Ambiente:** o contexto Python/plataforma está correto (`env`).",
        "ru": "- **Gate 1 – Окружение:** контекст Python/платформы корректен (`env`).",
        "zh-CN": "- **Gate 1 – 环境：** Python/平台上下文正确（`env`）。",
        "hi": "- **Gate 1 – वातावरण:** Python/प्लेटफ़ॉर्म संदर्भ सही है (`env`)।",
        "ja": "- **Gate 1 – 環境:** Python/プラットフォームの文脈が正しい（`env`）。",
    },
    "- **Gate 2 – Scientific sanity:** baseline model behavior is reproducible (`validate`).": {
        "es": "- **Gate 2 – Solidez científica:** el comportamiento base del modelo es reproducible (`validate`).",
        "it": "- **Gate 2 – Solidità scientifica:** il comportamento baseline del modello è riproducibile (`validate`).",
        "fr": "- **Gate 2 – Rigueur scientifique :** le comportement de base du modèle est reproductible (`validate`).",
        "pt-BR": "- **Gate 2 – Sanidade científica:** o comportamento base do modelo é reproduzível (`validate`).",
        "ru": "- **Gate 2 – Научная валидность:** базовое поведение модели воспроизводимо (`validate`).",
        "zh-CN": "- **Gate 2 – 科学校验：** 基线模型行为可复现（`validate`）。",
        "hi": "- **Gate 2 – वैज्ञानिक सुदृढ़ता:** बेसलाइन मॉडल व्यवहार पुनरुत्पादित हो सकता है (`validate`)।",
        "ja": "- **Gate 2 – 科学的妥当性:** ベースラインモデル挙動は再現可能（`validate`）。",
    },
    "- **Gate 3 – Source reliability:** market data + fallback chain are reachable (`preflight --market ALL`).": {
        "es": "- **Gate 3 – Fiabilidad de fuentes:** datos de mercado + cadena fallback disponibles (`preflight --market ALL`).",
        "it": "- **Gate 3 – Affidabilità delle fonti:** dati di mercato + catena fallback raggiungibili (`preflight --market ALL`).",
        "fr": "- **Gate 3 – Fiabilité des sources :** données de marché + chaîne de fallback accessibles (`preflight --market ALL`).",
        "pt-BR": "- **Gate 3 – Confiabilidade de fonte:** dados de mercado + cadeia fallback acessíveis (`preflight --market ALL`).",
        "ru": "- **Gate 3 – Надёжность источников:** рыночные данные + fallback-цепочка доступны (`preflight --market ALL`).",
        "zh-CN": "- **Gate 3 – 来源可靠性：** 市场数据 + fallback 链可达（`preflight --market ALL`）。",
        "hi": "- **Gate 3 – स्रोत विश्वसनीयता:** मार्केट डेटा + fallback chain उपलब्ध हैं (`preflight --market ALL`)।",
        "ja": "- **Gate 3 – ソース信頼性:** 市場データ + フォールバックチェーンに到達可能（`preflight --market ALL`）。",
    },
    "- **Gate 4 – Runtime execution:** live loop runs with known input history (`live`).": {
        "es": "- **Gate 4 – Ejecución runtime:** el bucle live corre con historial de entrada conocido (`live`).",
        "it": "- **Gate 4 – Esecuzione runtime:** il loop live gira con storico input noto (`live`).",
        "fr": "- **Gate 4 – Exécution runtime :** la boucle live tourne avec un historique d’entrée connu (`live`).",
        "pt-BR": "- **Gate 4 – Execução runtime:** o loop live roda com histórico de entrada conhecido (`live`).",
        "ru": "- **Gate 4 – Runtime-исполнение:** live-цикл работает с известной входной историей (`live`).",
        "zh-CN": "- **Gate 4 – Runtime 执行：** live 循环使用已知输入历史运行（`live`）。",
        "hi": "- **Gate 4 – रनटाइम निष्पादन:** live लूप ज्ञात इनपुट हिस्ट्री के साथ चलता है (`live`)।",
        "ja": "- **Gate 4 – ランタイム実行:** 既知の入力履歴で live ループが動作（`live`）。",
    },
    "- **Gate 5 – Adversarial confidence:** latency/failover targets hold under stress (`stress_test_suite.py`).": {
        "es": "- **Gate 5 – Confianza adversarial:** objetivos de latencia/failover se mantienen bajo estrés (`stress_test_suite.py`).",
        "it": "- **Gate 5 – Fiducia avversariale:** i target latenza/failover reggono sotto stress (`stress_test_suite.py`).",
        "fr": "- **Gate 5 – Confiance adversariale :** les cibles latence/failover tiennent sous stress (`stress_test_suite.py`).",
        "pt-BR": "- **Gate 5 – Confiança adversarial:** metas de latência/failover se mantêm sob estresse (`stress_test_suite.py`).",
        "ru": "- **Gate 5 – Адверсариальная уверенность:** цели latency/failover выдерживаются под стрессом (`stress_test_suite.py`).",
        "zh-CN": "- **Gate 5 – 对抗置信度：** 延迟/故障切换目标在压力下可保持（`stress_test_suite.py`）。",
        "hi": "- **Gate 5 – एडवर्सेरियल भरोसा:** latency/failover लक्ष्य स्ट्रेस में टिकते हैं (`stress_test_suite.py`)।",
        "ja": "- **Gate 5 – 敵対的信頼性:** latency/failover 目標がストレス下でも維持（`stress_test_suite.py`）。",
    },

    "- **iPhone (best effort)**: use shell apps such as iSH / a-Shell. Termux-specific notification hooks are not available there.": {
        "es": "- **iPhone (mejor esfuerzo):** usa apps shell como iSH / a-Shell. Los hooks de notificación específicos de Termux no están disponibles allí.",
        "it": "- **iPhone (best effort):** usa app shell come iSH / a-Shell. Gli hook di notifica specifici di Termux non sono disponibili lì.",
        "fr": "- **iPhone (best effort) :** utilisez des apps shell comme iSH / a-Shell. Les hooks de notification spécifiques à Termux n’y sont pas disponibles.",
        "pt-BR": "- **iPhone (best effort):** use apps de shell como iSH / a-Shell. Hooks de notificação específicos do Termux não estão disponíveis lá.",
        "ru": "- **iPhone (best effort):** используйте shell-приложения, такие как iSH / a-Shell. Специфичные для Termux хуки уведомлений там недоступны.",
        "zh-CN": "- **iPhone（尽力而为）：** 可使用 iSH / a-Shell 等 shell 应用。Termux 专用通知钩子在该平台不可用。",
        "hi": "- **iPhone (best effort):** iSH / a-Shell जैसे shell ऐप्स का उपयोग करें। Termux-विशिष्ट notification hooks वहाँ उपलब्ध नहीं हैं।",
        "ja": "- **iPhone（ベストエフォート）:** iSH / a-Shell などのシェルアプリを使用。Termux 固有の通知フックは利用できません。",
    },
    "- **Windows / Linux / macOS**: use the same CLI commands; run via tmux/scheduler/cron for persistence.": {
        "es": "- **Windows / Linux / macOS**: usa los mismos comandos CLI; ejecútalos vía tmux/scheduler/cron para persistencia.",
        "it": "- **Windows / Linux / macOS**: usa gli stessi comandi CLI; esegui via tmux/scheduler/cron per persistenza.",
        "fr": "- **Windows / Linux / macOS** : utilisez les mêmes commandes CLI ; exécutez via tmux/scheduler/cron pour la persistance.",
        "pt-BR": "- **Windows / Linux / macOS**: use os mesmos comandos CLI; execute via tmux/scheduler/cron para persistência.",
        "ru": "- **Windows / Linux / macOS**: используйте те же CLI-команды; запускайте через tmux/scheduler/cron для персистентности.",
        "zh-CN": "- **Windows / Linux / macOS**：使用同一套 CLI 命令；通过 tmux/scheduler/cron 保持持续运行。",
        "hi": "- **Windows / Linux / macOS**: वही CLI कमांड्स उपयोग करें; निरंतरता के लिए tmux/scheduler/cron से चलाएँ।",
        "ja": "- **Windows / Linux / macOS**: 同じ CLI コマンドを使用し、永続運用には tmux/scheduler/cron 経由で実行します。",
    },
    "Optional for COFFEE source quality:": {
        "es": "Opcional para mejorar la calidad de la fuente COFFEE:",
        "it": "Opzionale per migliorare la qualità della fonte COFFEE:",
        "fr": "Optionnel pour améliorer la qualité de la source COFFEE :",
        "pt-BR": "Opcional para melhorar a qualidade da fonte COFFEE:",
        "ru": "Опционально для повышения качества источника COFFEE:",
        "zh-CN": "可选：用于提升 COFFEE 数据源质量：",
        "hi": "COFFEE स्रोत गुणवत्ता सुधार के लिए वैकल्पिक:",
        "ja": "COFFEE ソース品質向上のための任意設定：",
    },
    "Run the scientific validation pipeline:": {
        "es": "Ejecuta el pipeline de validación científica:",
        "it": "Esegui la pipeline di validazione scientifica:",
        "fr": "Exécutez le pipeline de validation scientifique :",
        "pt-BR": "Execute o pipeline de validação científica:",
        "ru": "Запустите научный валидационный пайплайн:",
        "zh-CN": "运行科学验证流水线：",
        "hi": "वैज्ञानिक वैलिडेशन पाइपलाइन चलाएँ:",
        "ja": "科学的バリデーションパイプラインを実行：",
    },
    "You can now explore TPM behavior interactively in the browser:": {
        "es": "Ahora puedes explorar el comportamiento de TPM de forma interactiva en el navegador:",
        "it": "Ora puoi esplorare il comportamento TPM in modo interattivo nel browser:",
        "fr": "Vous pouvez désormais explorer le comportement TPM de manière interactive dans le navigateur :",
        "pt-BR": "Agora você pode explorar o comportamento do TPM de forma interativa no navegador:",
        "ru": "Теперь вы можете интерактивно изучать поведение TPM в браузере:",
        "zh-CN": "现在你可以在浏览器中交互式探索 TPM 行为：",
        "hi": "अब आप ब्राउज़र में TPM व्यवहार को इंटरैक्टिव तरीके से देख सकते हैं:",
        "ja": "ブラウザで TPM の挙動をインタラクティブに確認できます：",
    },
    "Includes:": {
        "es": "Incluye:", "it": "Include:", "fr": "Comprend :", "pt-BR": "Inclui:", "ru": "Включает:", "zh-CN": "包含：", "hi": "इसमें शामिल है:", "ja": "含まれるもの："
    },
    "- Single agent weak-signal anomaly view": {
        "es": "- Vista de anomalías de señal débil en agente único",
        "it": "- Vista anomalie weak-signal per singolo agente",
        "fr": "- Vue d’anomalies weak-signal en agent unique",
        "pt-BR": "- Visão de anomalias de sinal fraco em agente único",
        "ru": "- Вид аномалий слабых сигналов для одиночного агента",
        "zh-CN": "- 单代理弱信号异常视图",
        "hi": "- सिंगल एजेंट कमजोर-सिग्नल एनॉमली व्यू",
        "ja": "- 単一エージェントの弱信号アノマリービュー",
    },
    "- Mini swarm (BTC/COFFEE/VOL) consensus pressure": {
        "es": "- Mini enjambre (BTC/COFFEE/VOL) con presión de consenso",
        "it": "- Mini sciame (BTC/COFFEE/VOL) con pressione di consenso",
        "fr": "- Mini essaim (BTC/COFFEE/VOL) avec pression de consensus",
        "pt-BR": "- Mini enxame (BTC/COFFEE/VOL) com pressão de consenso",
        "ru": "- Мини-рой (BTC/COFFEE/VOL) и давление консенсуса",
        "zh-CN": "- 迷你群体（BTC/COFFEE/VOL）共识压力",
        "hi": "- मिनी स्वार्म (BTC/COFFEE/VOL) कंसेंसस दबाव",
        "ja": "- ミニスウォーム（BTC/COFFEE/VOL）のコンセンサス圧",
    },
    "- Cross-domain transfer resonance (synthetic finance/weather/health)": {
        "es": "- Resonancia de transferencia entre dominios (sintético: finanzas/clima/salud)",
        "it": "- Risonanza di trasferimento cross-domain (sintetico: finanza/meteo/salute)",
        "fr": "- Résonance de transfert cross-domain (synthétique : finance/météo/santé)",
        "pt-BR": "- Ressonância de transferência entre domínios (sintético: finanças/clima/saúde)",
        "ru": "- Междоменный трансфер-резонанс (синтетика: финансы/погода/здоровье)",
        "zh-CN": "- 跨域迁移共振（合成：金融/天气/健康）",
        "hi": "- क्रॉस-डोमेन ट्रांसफर रेज़ोनेंस (सिंथेटिक: फाइनेंस/मौसम/हेल्थ)",
        "ja": "- クロスドメイン転移共鳴（合成：金融/天気/ヘルス）",
    },

    "- Transfer entropy module for cross-market causal analysis.": {
        "es": "- Módulo de entropía de transferencia para análisis causal entre mercados.",
        "it": "- Modulo di transfer entropy per analisi causale cross-market.",
        "fr": "- Module de transfer entropy pour l’analyse causale inter-marchés.",
        "pt-BR": "- Módulo de entropia de transferência para análise causal entre mercados.",
        "ru": "- Модуль transfer entropy для межрыночного каузального анализа.",
        "zh-CN": "- 用于跨市场因果分析的传递熵模块。",
        "hi": "- क्रॉस-मार्केट कारणात्मक विश्लेषण के लिए ट्रांसफर-एंट्रॉपी मॉड्यूल।",
        "ja": "- クロスマーケット因果分析のための Transfer Entropy モジュール。",
    },
    "- Optimizer with policy updates based on historical performance.": {
        "es": "- Optimizador con actualizaciones de política basadas en rendimiento histórico.",
        "it": "- Ottimizzatore con aggiornamenti di policy basati sulle performance storiche.",
        "fr": "- Optimiseur avec mises à jour de policy basées sur la performance historique.",
        "pt-BR": "- Otimizador com atualizações de policy baseadas em desempenho histórico.",
        "ru": "- Оптимизатор с обновлениями policy на основе исторической производительности.",
        "zh-CN": "- 基于历史表现进行策略更新的优化器。",
        "hi": "- ऐतिहासिक प्रदर्शन के आधार पर policy अपडेट वाला ऑप्टिमाइज़र।",
        "ja": "- 履歴パフォーマンスに基づくポリシー更新付きオプティマイザ。",
    },
    "- In complex, chaotic systems, early-warning signal is often hidden in the **micro-residual**: tiny deviations, weak correlations, almost-empty data points.": {
        "es": "- En sistemas complejos y caóticos, la señal temprana suele ocultarse en el **micro-residual**: pequeñas desviaciones, correlaciones débiles y puntos casi vacíos.",
        "it": "- Nei sistemi complessi e caotici, il segnale di early-warning è spesso nascosto nel **micro-residual**: piccole deviazioni, correlazioni deboli e datapoint quasi vuoti.",
        "fr": "- Dans les systèmes complexes et chaotiques, le signal d’alerte précoce est souvent caché dans le **micro-résiduel** : petites déviations, corrélations faibles et points quasi vides.",
        "pt-BR": "- Em sistemas complexos e caóticos, o sinal de alerta precoce costuma ficar no **micro-residual**: desvios pequenos, correlações fracas e pontos quase vazios.",
        "ru": "- В сложных хаотических системах ранний сигнал часто скрыт в **micro-residual**: малых отклонениях, слабых корреляциях и почти пустых точках данных.",
        "zh-CN": "- 在复杂且混沌的系统中，早期预警信号常隐藏在 **微残差** 中：细微偏差、弱相关、近乎空白的数据点。",
        "hi": "- जटिल और कैओटिक सिस्टम में early-warning संकेत अक्सर **micro-residual** में छिपे होते हैं: सूक्ष्म विचलन, कमजोर सहसंबंध, लगभग-खाली डेटा पॉइंट्स।",
        "ja": "- 複雑でカオスな系では、早期警告シグナルはしばしば **micro-residual**（微小偏差・弱い相関・ほぼ空のデータ点）に隠れます。",
    },
    "- TPM evaluates not only a value itself, but the **change of relationships over time, source quality, regime, and causal neighborhood**.": {
        "es": "- TPM no evalúa solo el valor, sino también el **cambio de relaciones en el tiempo, la calidad de fuente, el régimen y el vecindario causal**.",
        "it": "- TPM valuta non solo il valore, ma anche il **cambiamento delle relazioni nel tempo, qualità fonte, regime e vicinato causale**.",
        "fr": "- TPM évalue non seulement une valeur, mais aussi le **changement des relations dans le temps, la qualité des sources, le régime et le voisinage causal**.",
        "pt-BR": "- O TPM avalia não só o valor em si, mas também a **mudança das relações ao longo do tempo, qualidade da fonte, regime e vizinhança causal**.",
        "ru": "- TPM оценивает не только само значение, но и **изменение связей во времени, качество источника, режим и каузальное соседство**.",
        "zh-CN": "- TPM 不仅评估单个数值，还评估**关系随时间变化、来源质量、状态区间与因果邻域**。",
        "hi": "- TPM केवल मान को नहीं, बल्कि **समय के साथ संबंधों का परिवर्तन, स्रोत गुणवत्ता, रेजीम और causal neighborhood** भी आकलित करता है।",
        "ja": "- TPM は値そのものだけでなく、**時間的関係変化・ソース品質・レジーム・因果近傍**も評価します。",
    },
    "Important correctness note: TPM does **not** magically predict the future. It aims for **earlier probabilistic detection** of regime shifts, breakouts, and disruptions — when data quality and validation gates are satisfied.": {
        "es": "Nota de corrección importante: TPM **no** predice mágicamente el futuro. Busca **detección probabilística temprana** de cambios de régimen, breakouts y disrupciones, cuando se cumplen calidad de datos y gates de validación.",
        "it": "Nota importante di correttezza: TPM **non** predice magicamente il futuro. Mira a una **rilevazione probabilistica anticipata** di cambi regime, breakout e disruption, quando qualità dati e gate di validazione sono soddisfatti.",
        "fr": "Note importante : TPM **ne** prédit pas magiquement le futur. Il vise une **détection probabiliste plus précoce** des changements de régime, breakouts et disruptions lorsque qualité des données et gates de validation sont respectés.",
        "pt-BR": "Nota importante: o TPM **não** prevê o futuro magicamente. Ele busca **detecção probabilística antecipada** de mudanças de regime, breakouts e disrupções quando qualidade de dados e gates de validação são atendidos.",
        "ru": "Важное уточнение: TPM **не** предсказывает будущее магически. Цель — **более раннее вероятностное обнаружение** смены режимов, пробоев и сбоев при соблюдении качества данных и validation-gates.",
        "zh-CN": "重要说明：TPM **并不**会“神奇预测未来”。其目标是在数据质量与验证 gate 满足时，实现对状态切换、突破和扰动的**更早期概率检测**。",
        "hi": "महत्वपूर्ण स्पष्टता: TPM भविष्य की **जादुई** भविष्यवाणी नहीं करता। इसका लक्ष्य डेटा गुणवत्ता और validation gates पूरे होने पर रेजीम बदलाव, breakout और disruption की **पहले से संभाव्य पहचान** है।",
        "ja": "重要な正確性メモ：TPM は未来を魔法のように予測**しません**。データ品質と検証ゲートが満たされる場合に、レジーム変化・ブレイクアウト・破綻の**より早い確率的検知**を目指します。",
    },
    '- Every profession can be modeled as a "market" with domain-specific features, nodes, correlations, and anomalies': {
        "es": '- Cada profesión puede modelarse como un "mercado" con rasgos de dominio, nodos, correlaciones y anomalías',
        "it": '- Ogni professione può essere modellata come un "mercato" con feature di dominio, nodi, correlazioni e anomalie',
        "fr": '- Chaque profession peut être modélisée comme un "marché" avec ses variables, nœuds, corrélations et anomalies',
        "pt-BR": '- Cada profissão pode ser modelada como um "mercado" com atributos de domínio, nós, correlações e anomalias',
        "ru": '- Каждую профессию можно моделировать как "рынок" со специфичными признаками, узлами, корреляциями и аномалиями',
        "zh-CN": '- 每个职业都可建模为一个"市场"：含领域特征、节点、相关性与异常',
        "hi": '- प्रत्येक पेशे को डोमेन-विशिष्ट फीचर्स, नोड्स, सहसंबंध और एनॉमलीज़ वाले "मार्केट" की तरह मॉडल किया जा सकता है',
        "ja": '- すべての職種は、ドメイン固有特徴・ノード・相関・異常を持つ"市場"としてモデル化可能',
    },
    "- Specialized TPM agents can learn across domains while preserving local professional logic and ethics": {
        "es": "- Agentes TPM especializados pueden aprender entre dominios preservando lógica y ética profesional local",
        "it": "- Agenti TPM specializzati possono apprendere tra domini mantenendo logica professionale locale ed etica",
        "fr": "- Des agents TPM spécialisés peuvent apprendre entre domaines en conservant logique professionnelle locale et éthique",
        "pt-BR": "- Agentes TPM especializados podem aprender entre domínios preservando lógica profissional local e ética",
        "ru": "- Специализированные TPM-агенты могут обучаться между доменами, сохраняя локальную профессиональную логику и этику",
        "zh-CN": "- 专用 TPM 代理可跨域学习，同时保留本地专业逻辑与伦理",
        "hi": "- विशेषीकृत TPM एजेंट डोमेन्स के बीच सीख सकते हैं, जबकि स्थानीय पेशेवर लॉजिक और एथिक्स बनाए रखते हैं",
        "ja": "- 専門 TPM エージェントは、地域の職業ロジックと倫理を保ちながらドメイン横断学習が可能",
    },
    "### 100 professions as TPM target spaces": {
        "es": "### TPM como espacio objetivo para 100 profesiones",
        "it": "### 100 professioni come spazi obiettivo TPM",
        "fr": "### 100 professions comme espaces cibles TPM",
        "pt-BR": "### 100 profissões como espaços-alvo TPM",
        "ru": "### 100 профессий как целевые пространства TPM",
        "zh-CN": "### 100 个职业作为 TPM 目标空间",
        "hi": "### TPM लक्ष्य-क्षेत्र के रूप में 100 पेशे",
        "ja": "### TPMターゲット空間としての100職種",
    },
    "| # | Profession | TPM data analog | Anomaly/pattern-detection target |": {
        "es": "| # | Profesión | Análogo de datos TPM | Objetivo de detección de anomalías/patrones |",
        "it": "| # | Professione | Analogo dati TPM | Target di rilevamento anomalie/pattern |",
        "fr": "| # | Profession | Analogue de données TPM | Cible de détection d’anomalies/patterns |",
        "pt-BR": "| # | Profissão | Análogo de dados TPM | Alvo de detecção de anomalias/padrões |",
        "ru": "| # | Профессия | TPM-аналог данных | Цель обнаружения аномалий/паттернов |",
        "zh-CN": "| # | 职业 | TPM 数据类比 | 异常/模式检测目标 |",
        "hi": "| # | पेशा | TPM डेटा अनुरूप | एनॉमली/पैटर्न डिटेक्शन लक्ष्य |",
        "ja": "| # | 職種 | TPMデータ類推 | 異常/パターン検知ターゲット |",
    },
    "### Country-fit notes (profession equivalence across jurisdictions)": {
        "es": "### Notas country-fit (equivalencia profesional entre jurisdicciones)",
        "it": "### Note country-fit (equivalenza professionale tra giurisdizioni)",
        "fr": "### Notes country-fit (équivalence des professions entre juridictions)",
        "pt-BR": "### Notas country-fit (equivalência profissional entre jurisdições)",
        "ru": "### Country-fit заметки (эквивалентность профессий между юрисдикциями)",
        "zh-CN": "### 国家适配说明（跨司法辖区职业等价）",
        "hi": "### Country-fit नोट्स (विभिन्न न्यायक्षेत्रों में पेशागत समतुल्यता)",
        "ja": "### 国別適合ノート（法域間の職種等価）",
    },
    "### Philosophical-scientific outlook": {
        "es": "### Perspectiva filosófico-científica",
        "it": "### Prospettiva filosofico-scientifica",
        "fr": "### Perspective philosophico-scientifique",
        "pt-BR": "### Perspectiva filosófico-científica",
        "ru": "### Философско-научный взгляд",
        "zh-CN": "### 哲学与科学视角",
        "hi": "### दार्शनिक-वैज्ञानिक दृष्टिकोण",
        "ja": "### 哲学・科学的展望",
    },
}

LOCALE_FILES = {
    "es": "README.es.md",
    "it": "README.it.md",
    "fr": "README.fr.md",
    "pt-BR": "README.pt-BR.md",
    "ru": "README.ru.md",
    "zh-CN": "README.zh-CN.md",
    "hi": "README.hi.md",
    "ja": "README.ja.md",
}


def apply_locale(locale: str, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    changes = 0
    for src, mapping in COMMON.items():
        dst = mapping[locale]
        if src in text and dst != src:
            text = text.replace(src, dst)
            changes += 1
    path.write_text(text, encoding="utf-8")
    return changes


def main() -> int:
    total = 0
    for locale, name in LOCALE_FILES.items():
        path = I18N / name
        c = apply_locale(locale, path)
        total += c
        print(f"{name}: {c} replacement groups applied")
    print(f"Total replacement groups applied: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
