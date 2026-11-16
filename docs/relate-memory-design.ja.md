# Relateによる関係付き想起：全体設計

[English](relate-memory-design.md) | [全体設計](architecture.ja.md) | [実験の入口](../experiments/relate-memory/README.ja.md)

設計日：2026-11-17 JST。実装・実測の現在地は[実装状況](implementation-status.ja.md)だけを正本とする。
以下は実装担当AIへの設計であり、既存CLIに未実装のコマンドがあるという案内ではない。

## 判断

**SQLiteを正本として維持し、Relateを再構築可能な関係索引として追加する。**
独立した実験パッケージ「Connected Recall」を experiments/relate-memory/ に置く。
既存のcapture、Light/Deep、独立verification、atomic adoptionは変更しない。
Relateは何を思い出すかと、その根拠経路を選ぶ。何が採用済み・利用可能かはSQLite側が決める。
[ADR 0002](decisions/0002-assume-agent-forgets.md)の「対象agentは忘れる」前提を維持する。

| 案 | 利点 | 欠点・期限への影響 | 判断 |
|---|---|---|---|
| A. Relateへ正本を全面移行 | 採用状態・来歴・探索を一つのDBで扱える。関係の更新を同じtransactionに置ける | SQLiteの受領、CAS採用、忘却、rollback、再開契約を再実装・移行する必要。ストア互換性と復旧のリスクが大きい | 今回は採用しない。グラフの効果が実測できてから別ADRで判断 |
| B. SQLite正本＋Relate関係索引 | 既存の採用境界を維持。関係探索を実際の想起へ使用できる。索引を捨てても原証拠は失わない | 二重保存、索引の鮮度、削除伝播、最終再検査が必要 | **推奨。小規模な全再構築と明示fallbackから始める** |
| C. 凍結exportをRelateへ読み込む独立ビューア | 最短で可視化・説明・審査員の探索を作れる。coreへの影響が小さい | graphを外しても想起結果が変わらないと、主用途への貢献が伝わりにくい | Bの初期到達点／縮退案。展示だけで想起改善を主張しない |

## 調べた現行実装と接続先

設計基点は[9853c4e](https://github.com/moruku36/agent-sleep-lab/tree/9853c4e993fefadab003c52b5a30729c6ddfa683)。
復旧用の固定情報は[BASELINE](../experiments/relate-memory/BASELINE.md)を参照する。

- [AdoptionStore](../src/agent_sleep_lab/adoption_store.py)と[retrieval](../src/agent_sleep_lab/retrieval.py)は合成データ用。scopeは project と task_family の完全一致。
- retrievalは同一SQLite read transactionで現在policy、active snapshot、受領、記憶hash、原証拠と全祖先を検査する。順位は決定的な語句一致、予算はUTF-8 byte。
- [memory schema](../schemas/memory.schema.json)にはsupersedes、[provenance](../schemas/provenance.schema.json)にはroot、derived_from、許可、partitionが既にある。
- [ReferenceUseJournal](../src/agent_sleep_lab/reference_use.py)は利用意図・返却等の記録であり、意味的利用や有用性を自動証明しない。
- [公開文書store](public-document-lifecycle.ja.md)は別形式・別契約。最初の実験では接続しない。実データを合成と偽って流さない。

MVPは合成AdoptionStoreを入力にする。この選択は、現在の全agentにRelateを配備する判断ではない。
実運用の公開文書経路へのadapterは、MVP後に専用のexport・削除・利用許可契約を設計する。

## 配置と依存方向

~~~text
src/agent_sleep_lab/                 既存core。Relateをimportしない
schemas/ configs/ tests/             既存契約・設定・回帰を維持
docs/decisions/0006-...              保存方式と撤退の判断
docs/relate-memory-design*.md        この設計
experiments/relate-memory/
  README.md / README.ja.md           別の導入入口
  BASELINE.md / REUSE.md             固定基点・既存資産の開示
  pyproject.toml / requirements.lock 実装時に追加する別依存
  src/asl_connected_recall/          実装時に追加
    core_read_bridge.py              core形式を1か所で吸収
    projection.py                   export → Relate
    retrieval.py                    bounded traversal＋順位
    bundle.py                       core再検査＋束縛
    cli.py                          明示実行のみ
  configs/                          graph専用設定（実装時）
  tests/                            拡張の選択テスト（実装時）
  fixtures/                         合成入力と評価課題（実装時）
  submission/                       公開許可した審査用store等（実装時）
  .state/                           private生成物、Git対象外
~~~

上記の「実装時」は予定配置。空の実装や偽の実行結果を作って完成扱いしない。
coreから実験への依存は禁止。実験は固定したcore版へ依存する。
rootの必須依存、既定CLI、DB形式、既存schemaにはRelateを追加しない。
graph用設定は実験内に限定し、既存コマンドへ未実装のflagを案内しない。

単一のgraph所有プロセスが接続を開き、同じthreadで使用・closeする。複数agentが同じファイルを直接openしない。
MVPは明示的な直列CLI実行とし、並行起動は待機上限付きlockまたはbusyで拒否。
後で常駐化する場合も、単一所有者への要求を直列化する別段階とする。

## Relateの前提

確認した上流は[5f8eaf1](https://github.com/relatedb/relate/tree/5f8eaf129a6490bd4b6664cffc7b9498e2c6b93f)。
[制約](https://github.com/relatedb/relate/blob/5f8eaf129a6490bd4b6664cffc7b9498e2c6b93f/docs/limitations.md)では、
single-process、メモリ内working set、競合writerの明示エラーを説明している。
「transactionがある」ことを、独立した複数agentプロセスの同時ファイル書込み保証と解釈しない。

第一候補はPython埋込み＋単一 .rl ファイル。WASM・Bolt・HTTP・MCP・vector検索はMVPの依存にしない。
Python APIの接続にはthread affinityがある。個々の公開面と版の挙動は別途受入する。
上流READMEとPython referenceには配布方法・永続パスの説明差があるため、実装初日に
OS／Python／配布wheel／Relate版を固定し、作成→commit→close→別processでreopenを確認する。
.rl が選択したbindingで使えなければ、公式のdirectory形式へ切り替える。
いずれも全ファイルを整合した停止時点で保存する。[公式backup資料](https://github.com/relatedb/relate/blob/5f8eaf129a6490bd4b6664cffc7b9498e2c6b93f/docs/guides/backup-restore.md)

## グラフモデル

IDはDB内部の連番に依存しない。共通namespaceは
store_instance_id＋project＋task_family＋partition。版付き対象には論理ID＋内容hashを加える。
store_instance_idはadapterの明示設定とexport manifestで束縛する識別であり、認証ではない。
同一文字列のIDやURIでも別scope・別storeのデータを勝手に統合しない。

| ノード | 主な属性 | 元データと意味 |
|---|---|---|
| Scope | project, task_family, partition, store_instance_id | 認可判定の代わりではなく、探索を閉じる境界 |
| Snapshot | snapshot_sha256, parent_sha256, policy_sha256 | 採用版。current表示はmanifestとSQLiteで照合 |
| MemoryVersion | memory_id, memory_sha256, kind, valid_until | 不変の記憶版。active状態はSnapshotとの所属関係で表す |
| EvidenceVersion | event_id, event_sha256, root_id, origin, observed_at | 原証拠／派生証拠。回数より独立rootの違いを重視 |
| SourceVersion | source_id, source_sha256, locator_ref | 出所の固定版。URLだけを出典の同一性にしない |
| Task | task_id, task_input_sha256, task_family | 新旧の作業単位。現タスクの答えは格納しない |
| Entity | entity_id, kind, canonical_name | 合成例のfile/API/decision等。scope内でのみ同定 |
| UseEvent | use_id, stage, bundle_sha256, outcome_ref | prepared/dispatched/completed/unknown/invalidated等の観測 |
| Agent | agent_id, role | hostが付けた主体表示。権限付与や認証を意味しない |

| エッジ（方向） | 意味・制約 |
|---|---|
| Scope → HAS_SNAPSHOT → Snapshot | 同scopeの版。複数scopeを混ぜない |
| Snapshot → HAS_MEMBER → MemoryVersion | member_state、記憶hash、verification receipt参照を保持 |
| MemoryVersion → SUPPORTED_BY → EvidenceVersion | 既存のevidence参照。locatorを持ち、原証拠へ戻れる |
| EvidenceVersion → DERIVED_FROM → EvidenceVersion | 子→親。再掲・要約を独立証拠に数えない |
| EvidenceVersion → FROM_SOURCE → SourceVersion | provenanceのsource固定版 |
| 新MemoryVersion → SUPERSEDES → 旧MemoryVersion | 採用済みsupersedesに由来。新しい方へ進むときは逆方向探索 |
| MemoryVersion → ABOUT → Entity | 根拠付きの対象同定。類似語だけで確定しない |
| Task → TARGETS → Entity | タスクが扱う対象 |
| Task → DEPENDS_ON → Task | 明示された依存。推測で追加しない |
| Task → HAS_USE → UseEvent | 作業ごとの利用過程 |
| UseEvent → INCLUDED_MEMORY → MemoryVersion | bundleに含まれたこと。意味的利用とは別 |
| UseEvent → BY_AGENT → Agent | 主体の表示 |
| UseEvent → REVIEWED_USE_OF → MemoryVersion | 独立した意味review受領がある場合のみ。MVPでは省略可能 |

Task/Entity/ABOUT/DEPENDS_ONは既存memory schemaに全て存在するfieldではない。
追加する関係assertionは実験用の合成sidecarに置き、ID・両端・根拠参照・review状態・hashを保存する。
MVPは手でreviewした合成関係だけを使う。LLMによる自動関係抽出や自動採用は後続。
UseEventからMemoryへ辿れても、成功した記憶だから正しいという昇格や、同一出典の水増しはしない。

本文はSQLiteから読む。graphにはID、関係、最小の公開可能な表示名を置き、
証拠本文・認証値・私的URIを無条件に複製しない。審査用だけは合成の短い説明を同梱できる。
関係・ID・表示名自体も機密になり得るので、索引も削除対象である。

## 索引生成・整合性・削除

SQLiteとRelateを跨ぐ原子transactionはない。coreのcommit成功とgraphの生成成功を分離する。
MVPは小さいscopeごとの**全再構築**。採用writerへのdual writeやoutbox追加を先に行わない。

1. CoreReadBridgeが一つのSQLite read snapshotから採用head、現在policy／除外、適格な記憶、
   根拠closure、必要最小限の履歴metadataをexportする。既存検査を共用し、別の簡易認可器を作らない。
2. manifestへcore形式／版、store_instance_id、scope、partition、snapshot hash、policy revision/hash、
   export hash、関係sidecar hash、graph schema、Relate版を記録する。
3. 新しい世代のgraphを専用pathへ生成し、edge両端、scope、ID重複、supersede cycleと根拠を検査する。
   順序・IDは決定的にし、同じexportの再処理で論理的重複を生まない。
4. writerをcloseして再openを確認。現在のSQLite head／policyを再読し、exportとの一致を確認する。
5. 不一致・中断なら世代を公開しない。成功した世代の小さなpointerだけをatomic replaceする。
   古いhandleがopen中の .rl ファイルを上書きしない。Windowsも同じ運用とする。

CoreReadBridgeは**新規実装が必要な契約**。現行retrieve_reference_bundleだけでは、
順位付け前の全適格集合・履歴metadataを外部へ公開するAPIになっていない。
既存の上限付きbundleを全exportと誤認したり、private helperの検査を省略コピーしないこと。
最初は固定core版の薄い実験adapterへ隔離する。必要な共用read APIをcoreへ追加する場合は
既存出力・既定動作を変えない小さな別commitとし、graph importをcoreに導入しない。
上限を超えるexportは明示拒否し、部分graphを完全な索引と呼ばない。

通常想起はmanifest一致を必須とする。graphが欠落・破損・古い・busyなら、
SQLiteが利用可能な場合だけ既存lexical retrievalへ明示fallbackし、理由を記録する。
SQLiteのpolicy・原証拠検査に失敗した場合はgraphから返さず停止する。

忘却／権限撤回はSQLite側を先に反映し、その時点からgraph経由でも返さない。
旧世代、表示cache、trace、exportの参照も無効化・掃除する。再構築で除外されたIDは復活させない。
MVPで物理消去できたと主張するのは検査した管理ファイルだけ。停止中processや外部copyの即時消去は保証しない。
公開するのは合成storeだけとし、私的記憶をGit履歴へ入れない。

## 想起アルゴリズム

graphは候補の発見と説明に実際に使う。可視化だけを作って「graph想起」としない。

1. hostがタスクのscope・partition・必要なentity IDを渡す。scopeを自由文や記憶から拡大しない。
2. 正本の状態fingerprintと一致するgraph世代を選ぶ。
3. 同じseed条件で、語句一致上位のMemoryVersionとTask → TARGETS → Entityを入口にする。
4. まず Entity ← ABOUT ← MemoryVersion で、語句が一致しないが同じ対象に関係する記憶を候補にする。
   Task → DEPENDS_ON → Task → HAS_USE → UseEvent → INCLUDED_MEMORY は補助候補であり、利用回数は真偽ではない。
5. 旧記憶をseedにした場合、SUPERSEDESを逆向きに辿って後継を見つける。
   snapshot所属と現在の適格性を検査し、古い内容を通常bundleへ入れない。
   履歴nodeは許可されたID等のmetadataだけを経路説明に使い、非activeの本文は返さない。
   分岐・cycle・未解決の競合を「最も新しい日付」で勝手に解決しない。
6. SUPPORTED_BY／DERIVED_FROM／FROM_SOURCEで根拠経路を添える。
   relevance用の探索深さと、採用適格性に必要な**全祖先検査**を混同しない。後者は既存境界を維持する。
7. 返すID/hashと、順位付けに使った経路の全ノード・エッジの根拠をSQLite／sidecarの現在状態で再検査する。
   scope外の中間ノード、失効した利用記録、撤回済み出典を通る経路も採用しない。
8. 決定的に順位を決め、SQLiteから本文を取得し、説明・出典を含めた全bundleのUTF-8 byteを計測する。
   不足時は順位の低い完全なrecordを落とす。truncateで根拠を切らない。

提案するMVP上限：seed 8、候補32、探索200ノード／400edge、関係探索3 hop、
supersede追跡8 hop、最終8記憶、bundle 8,192 UTF-8 byte。
値は性能実測ではなく初期設定。到達上限はtraceに記録し、黙って網羅性を主張しない。
path全体が長い利用経路は複数の固定templateに分けて上限を適用する。
timeoutをPython呼出しで確実に制御できるかは受入事項。できない場合は所有workerを期限付きで実行する。

順位は「明示task対象との関係 → seedとの距離 → 出典rootの重複抑制 → 語句一致 → 安定ID」から始め、
基準を評価前に固定する。単純な次数・PageRank・利用回数で上位を決めない。
現在の期限制御、policy、snapshot適格性は順位より前の必須条件。

実験bundleは既存v1へfieldを混ぜず、別のversioned envelopeにする。
snapshot/policy/graph generation/query template/関係sidecarの各hash、選択ID、理由path、fallbackを束縛する。
既存consumerへ渡す場合は、そのadapterがこの新形式を明示的に受け入れる段階が必要。
dispatch直前にも現在状態を再確認する。想起後の任意の外部行動まで原子的に保護できるとは主張しない。

~~~mermaid
flowchart LR
  T[新タスク] --> E[対象entity]
  E --> M[関係から見つけた記憶候補]
  M --> N[採用済みの後継記憶]
  N --> V[根拠と出所]
  N --> C[SQLiteで現在の適格性を再検査]
  V --> C
  C --> B[予算内の想起bundle＋理由path]
~~~

## 最小の作品と評価

一つの架空開発project、同じtask_family、開発担当／調査担当の2つの役割、
約20記憶とその根拠を合成fixtureにする。新しいagentランタイムを二つ作る必要はない。
一つのデモを最後まで完成させる：以前のタスクで得た制約を別agentの新タスクが想起し、
訂正後の記憶と出所を辿り、撤回後は出さない。

比較は同じSQLite snapshot・policy・入力・合計byte予算で、
L＝既存lexical、G＝同じseed＋関係展開、G-minus＝特定の有効edge型だけを無効化。
訂正・削除・scope安全性は全条件で等しく守る。baselineだけ古い記憶を許す比較にしない。
vectorは初回では使わず、embeddingの差と関係の寄与を混ぜない。

期待集合・必須の根拠経路は調整用fixtureとは別に固定する。
関係を効かせる例だけでなく、無関係な高次数nodeと、graphが役立たない例も含める。
必要記憶の取得、根拠pathの正当性、scope／失効違反、bundle byte、
build/retrieval時間・storeサイズを記録する。少数の合成例は機能実証であり一般的な性能改善ではない。
live agentの成功率・費用削減は実モデル応答と独立評価が必要で、未測定なら未測定と記す。

最初の受入は以下の5テーマから変更関連分だけ選ぶ。localとCIを二重計上し、
[既存の最大10ケース方針](testing-budget.ja.md)を守る。全履歴suiteを回さない。

1. 再構築→close/reopen→同じ論理ID/edgeとmanifest、再処理の重複なし。
2. 同じbudgetでgraphだけが関係を介して必要記憶を追加でき、edge除去で差が消える。
3. supersede／忘却／scope外の中間nodeを拒否し、古い索引でも内容を返さない。
4. 索引生成中断・世代不一致・busyで部分結果を公開せず、宣言したfallbackになる。
5. graph無効・依存未installでもcoreの既定経路が動き、SQLiteへgraph由来の変更がない。

## 3週間の実装順序

| 期間（JST、提案） | 完了させる単位 | 終了条件 |
|---|---|---|
| 11/18–20 | 接続可否と独立package。scope付きexport契約 | 固定版Relateのpersist/reopen、core無変更、export完全性が確認できる |
| 11/21–25 | graph投影・モデル・manifest・再構築 | 合成snapshotから審査可能な永続storeを作れる |
| 11/26–30 | 関係探索・SQLite再検査・fallback | 一つのtaskで理由付きbundleが返り、edge ablationが説明できる |
| 12/1–4 | 訂正／撤回と限定比較 | 選択受入、失敗経路、同条件の比較結果を保存 |
| 12/5–8 | 審査員手順と90秒demo | fresh環境でinstall→rebuild→inspect→compareが再現できる |
| 12/9–11 | 修正・提出物の凍結 | storeを再open、hash照合、動画・topic・開示内容を確認 |

残りは約25日。上表の実装を約3週間、最後を提出bufferに使う。
最初の3日でPython永続化が通らなければ固定CLIをadapterの代替にし、
12/1時点でG経路が動かなければCへ縮退して機能の範囲を正直に示す。
SQLite全面移行、vector、WASM UI、MCP公開、常駐schedule、全agent配備、実データ移行は期限後へ回す。

## 切り戻し

1. 実験CLI／workerだけを停止し、既存coreのCLI・adapterへ戻す。graphをcoreの必須起動条件にしない。
2. Relate依存は別venvにあるため、core環境をuninstall・再構築しない。
3. graphの .state は停止後に保管または破棄する。core SQLiteには索引側から書いていないので、DB復元は不要。
4. 既存開発はmainで継続し、実験実装は feature/relate-* 等の別branch・独立commit群で進める。
   撤退は実験commit群をrevertする。共有mainへのreset／force pushや、以後のcore改修の巻戻しはしない。
5. コードを固定基点へ戻しても、最新DBを古いcopyで上書きしない。
   coreの後続schema変更があれば、そのcore自身の互換性／復旧手順に従う。

## 主なリスクと代替

| リスク | 対応 |
|---|---|
| 二つのDBの不一致 | 小さい全再構築、世代manifest、現在SQLite再検査。将来増分化は別ADR |
| 関係の誤生成・prompt injection | 合成のreview済み関係から開始。graph本文を権限にしない。固定query templateとparameter使用 |
| 削除後もgraph／traceに残る | SQLiteで即時利用拒否、全派生物の無効化・掃除。物理削除の実測範囲を限定 |
| DBの競合・メモリ超過 | 単一所有process、scope別小graph、bounded traversal。vectorなし |
| RelateのAPI／保存形式変化 | 版と配布物hashを固定。rebuild可能な合成入力も同梱。CLI／directoryへ縮退可能 |
| coreのprivate helper依存 | 1つのversioned bridgeへ集約し、対応外coreを拒否。別storeの暗黙対応をしない |
| 審査にgraphの価値が伝わらない | graphで追加取得した記憶と理由path、同条件baseline・edge ablationを同じ画面に出す |
| 開発時間が基盤改修で消える | 一つのシナリオを優先し、索引・想起・説明以外の新基盤を増やさない |

## ハッカソンへの見せ方と確認事項

90秒の案：0–15秒で忘却・訂正の問題、15–45秒でL/Gの同条件比較と理由path、
45–65秒で訂正／撤回、65–90秒で永続storeを別processで開き再現手順を示す。
「記憶が多い」ではなく「どの関係で必要な記憶に辿り着き、なぜ今使ってよいか」を作品の中心にする。

案内ページの10/30/25/20/15点を設計上の目安にすると、
独創性＝根拠・訂正・利用の連結、関係30＝探索が想起内容を変えること、
完成度25＝一つのend-to-endとfallback、有用性20＝別taskへの引継ぎ、
再現性15＝合成入力＋永続store＋同条件比較となる。得点の保証ではない。

2026-11-17に[案内ページ](https://relate.devpost.com/)と[公式規約](https://relate.devpost.com/rules)を確認。
締切は2026-12-11 18:00 PST＝**12/12 11:00 JST**。
両ページに、既存作品の拡張可否と配点の記述差がある。規約は新規作品・期間内着手と
再利用資産の開示を要求し、均等配点とも記載する。採点方法とこの拡張の応募適格性は**主催者確認が必要**。
こちらから連絡・参加登録・提出は行わない。

新規拡張の開始日・diff・再利用範囲を[REUSE](../experiments/relate-memory/REUSE.md)で明示する。
既存agent-sleep-lab全体を期間内の新作として提出しない。
repoは公開でも[metadata](../pyproject.toml)はUNLICENSED。ライセンスを勝手に付け替えず、
所有者の選択と依存ライセンスの確認を提出準備に残す。

提出時には、公開topic relate、審査員が開ける永続store、版固定した再構築・照会手順、
1–2分の動画、既存資産とAI利用の開示を用意する。公開storeは新規合成データからだけ生成する。
保存mode、対応OS、install command、正確な成果物pathとhashは実装受入後に実験READMEへ記載する。
現時点の設計文書を、動作するRelate作品の代わりに提出しない。
