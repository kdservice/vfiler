# vfiler ドキュメント

`vfiler.py` は、Python標準ライブラリだけで動作するVZ風の端末ファイラー兼内蔵エディタです。
端末毎に常駐させることが出来、ESCキー、SHIFT+ENTERキーで起動が出来ます。
iTermのみの確認ですがjpg等の簡易表示も可能。

## 起動方法

### 通常起動

```bash
python3 /path/to/vfiler/vfiler.py
python3 /path/to/vfiler/vfiler.py /path/to/dir
```

引数なしではカレントディレクトリから起動します。引数にディレクトリを渡すと、そのディレクトリを開始位置にします。

### 1ペイン / 2ペイン指定

```bash
python3 /path/to/vfiler/vfiler.py --1 /path/to/dir
python3 /path/to/vfiler/vfiler.py --2 /left/path /right/path
```

`--1` はファイル一覧 + プレビューの1ペインモード、`--2` は左右2ペインモードで起動します。

### 内蔵エディタ / ビューア起動

```bash
python3 /path/to/vfiler/vfiler.py --e file.txt
python3 /path/to/vfiler/vfiler.py --v file.txt
```

`--e` は内蔵エディタで編集、`--v` は読み取り専用ビューアとして開きます。

### 常駐モード

```bash
python3 /path/to/vfiler/vfiler.py -z
```

常駐モードは端末TTYごとにサーバを起動します。常駐中に通常起動相当の `python3 vfiler.py` や `python3 vfiler.py file.txt` を実行すると、可能な場合は常駐側へ処理を転送します。

常駐転送を避けたい場合は `--no-resident` を付けます。

```bash
python3 /path/to/vfiler/vfiler.py --no-resident
```

### bash連携

```bash
source /path/to/vfiler/vfiler_bash_popup.sh
```

対話bashで読み込むと、常駐サーバを起動し、readlineキー割当を設定します。

| Shellキー | 動作 |
| --- | --- |
| `ESC` | ファイル名入力ポップアップを表示します。入力してEnterすると常駐エディタで開き、空Enterならカレントディレクトリを1ペインでファイラー表示します。編集中バッファがある場合はバッファ一覧も表示します。 |
| `ESC ?` | `ESC` と同じポップアップを表示します。 |
| `Shift+Enter` | ポップアップなしで前回の常駐ファイラー状態を開きます。2ペイン、検索結果、Git表示、ログ、ペイン幅などを保持します。ファイラー側で `Shift+Enter` すると選択項目をShell入力行へ返します。 |

iTerm2で `Shift+Enter` を使う場合は、Keys設定で `Send Escape Sequence` に `[13;2u` を割り当てます。

### その他の起動オプション

| オプション | 説明 |
| --- | --- |
| `--nostat` | `vfiler_stat.json` の読み書きを無効化します。 |
| `--self-test` | 非対話セルフテストを実行します。 |
| `--shell-popup [LABEL]` | 実験用のShellポップアップ入力を表示します。 |
| `--shell-popup-default TEXT` | `--shell-popup` の初期値を指定します。 |

## ファイラー

### 画面モード

| モード | 概要 |
| --- | --- |
| プレビューモード | 左にファイル一覧、右に選択項目のプレビューを表示します。 |
| 2ペインモード | 左右のディレクトリを並べて操作します。コピー、移動、同期、比較に使います。 |
| ログペイン | `Tab` でフォーカスします。コマンド実行結果や操作ログを表示し、入力欄からコマンド実行できます。 |
| 一時ビュー | 検索結果、Git表示、比較、重複表示、zip内表示などの一時的な一覧です。 |

### キー割当

| キー | 動作 |
| --- | --- |
| `1` | プレビューモードへ切替 |
| `2` | 2ペインモードへ切替。比較中は比較表示を閉じます。 |
| `Tab` | ファイル一覧、プレビュー、ログのフォーカスを切替 |
| `?` | ヘルプを表示 |
| `F1` | Filesメニュー |
| `F2` | Editメニュー |
| `F3` | Viewメニュー |
| `F4` | Gitメニュー |
| `F5` | 再読み込み。`thurupaths` 配下では `Y` 確認後に一覧取得します。 |
| `F6` | Launchメニュー |
| `F7` | ペインサイズ変更 |
| `F9` | 選択項目をファイルクリップボードへコピー |
| `Shift+F9` | 選択項目をファイルクリップボードへカット |
| `F10` | ファイルクリップボードを貼り付け |
| `F12` | 常駐エディタにバッファがある場合、次のエディタバッファを開きます。 |
| `↑` / `k` | カーソルを上へ移動 |
| `↓` / `j` | カーソルを下へ移動 |
| `Home` | 先頭へ移動 |
| `End` | 末尾へ移動 |
| `PageUp` | 1ページ上へ移動 |
| `PageDown` | 1ページ下へ移動 |
| `←` | 2ペインでは左ペインへ移動。プレビューモードでは一覧側へフォーカス。 |
| `→` | 2ペインでは右ペインへ移動。プレビューモードではプレビュー側へフォーカス。 |
| `Enter` | ディレクトリへ移動、zipを開く、ファイルを拡張子実行します。ログ入力がある場合はコマンド実行します。 |
| `Backspace` | 親ディレクトリへ移動。一時ビューでは一時ビューを閉じます。 |
| `\` `\` | 2回押しでルートへ移動 |
| `[` | ディレクトリ履歴を戻る |
| `]` | ディレクトリ履歴を進む |
| `Space` | 選択項目のマーク切替 |
| `a` / `A` | 全マーク切替 |
| `b` | ブックマーク一覧 |
| `B` | 現在ディレクトリをブックマーク追加 |
| `e` / `E` | 選択ファイルを内蔵エディタで開く |
| `v` / `V` | 選択ファイルをビューア表示、または2ペインで相手側プレビュー |
| `i` / `I` | 選択項目の情報表示 |
| `x` / `X` | ランチャー実行 |
| `g` / `G` | Git操作 |
| `s` / `S` | ソート選択 |
| `l` / `L` | ディレクトリジャンプ |
| `w` / `W` | プレビューモードでは折り返し切替、2ペインでは相手ペインを同じパスへ同期 |
| `y` / `Y` | `thurupaths` 指定ディレクトリのプレビュー一覧取得を許可 |
| `r` / `R` | リネーム |
| `n` / `N` | ディレクトリ作成 |
| `d` / `D` / `Delete` | 削除 |
| `c` / `C` | コピー |
| `m` / `M` | 移動 |
| `f` / `F` | 内容検索 |
| `/` | 名前フィルタ |
| `q` / `Q` / `ESC` | 終了。常駐モードのファイラーでは `ESC` は確認なしでShellへ戻ります。 |
| `Shift+Enter` | 常駐モードのファイラーで選択項目をShell入力行へ返してShellへ戻ります。 |

プレビューペインにフォーカスがある場合、`↑` / `↓` / `PageUp` / `PageDown` / `j` / `k` はプレビューをスクロールします。差分プレビューでは `n` / `N` で次の差分、`b` / `B` で前の差分へジャンプします。

ログペインにフォーカスがある場合、`Enter` はログ入力欄のコマンド実行、`ESC` は入力クリアまたはログフォーカス解除、`↑` / `↓` は履歴呼び出し、`PageUp` / `PageDown` はログスクロールです。

### メニュー

#### Files

| 項目 | 概要 |
| --- | --- |
| Open/Exec | 選択項目を開く、または拡張子実行します。 |
| View | ビューア表示します。 |
| Edit | 内蔵エディタで編集します。 |
| Tail | ファイル末尾追従表示を開始します。 |
| Information | サイズ、日時、パスなどの情報を表示します。 |
| Copy | 選択項目をコピーします。 |
| Merge Copy | ディレクトリ内容をマージコピーします。 |
| Move | 選択項目を移動します。 |
| Rename | 選択項目をリネームします。 |
| Mkdir | ディレクトリを作成します。 |
| Delete | 選択項目を削除します。 |
| Bookmark List | ブックマークから移動します。 |
| Bookmark Add | 現在ディレクトリをブックマークへ追加します。 |
| Reload DEF | 設定ファイルを再読み込みします。 |
| Restart | vfilerを再起動します。常駐モードでも有効です。 |
| Close/Quit | ファイラーを終了します。 |

#### Edit

| 項目 | 概要 |
| --- | --- |
| Mark All | 全項目をマークします。 |
| Clear Marks | マークを解除します。 |
| Copy/Cut | ファイルクリップボードへコピー/カットします。 |
| Paste | ファイルクリップボードを貼り付けます。 |
| Clip File Clear | ファイルクリップボードをクリアします。 |
| Path Copy | 選択項目のパス文字列をクリップします。 |
| Filename Copy | 選択項目のファイル名をクリップします。 |
| File Search | 内容検索結果を一覧表示します。 |
| Filename Search | ファイル名検索結果を一覧表示します。 |
| Bulk Name Replace | 複数ファイル名の文字列置換リネームを行います。 |
| Name Filter | 一覧の名前フィルタを設定します。 |

#### View

| 項目 | 概要 |
| --- | --- |
| Preview Mode | 1ペインプレビューへ切替 |
| Dual Mode | 2ペインへ切替 |
| Sort | ソート方法を選択 |
| Dir List | 登録ディレクトリ、ホーム、macOSの `/Volumes`、Windowsドライブなどへ移動 |
| Compare | 2ペインの内容比較 |
| Duplexes | 重複ファイル表示 |
| Preview Wrap / Sync Path | プレビューでは折り返し切替、2ペインではパス同期 |
| Line Number | プレビューの行番号表示切替 |
| Datetime | 日時表示切替 |
| Hide Empty Directories | 空ディレクトリ非表示切替 |
| Mouse Cursor | マウスクリックでのカーソル移動切替 |
| Wheel Scroll | ホイールスクロール切替 |
| Commit Id | Gitグラフ表示中のコミットID表示切替 |
| Graph Time | Gitグラフ表示中の時刻表示を相対/日時で切替 |

#### Git

| 項目 | 概要 |
| --- | --- |
| Status | Gitステータスを一覧表示 |
| Commit Command | `git commit` を実行 |
| Unmanaged Files | 未管理ファイル一覧 |
| Managed Files | 管理ファイル一覧 |
| Discard Changes | 変更破棄 |
| Manage File(s) | `git add` |
| Add ignore | `.gitignore` へ追加 |
| Unmanage File(s) | `git rm --cached` |
| File History | 選択ファイルの履歴 |
| Graph Tree | Gitロググラフ |
| Branch List | ブランチ一覧とcheckout |
| New Branch | ブランチ作成 |
| Merge Branch | ブランチmerge |
| Show Command | `git show` |
| Pull Command | `git pull` |
| Push Command | `git push` |
| Initialize | `git init` |
| Checkout Commit | Gitグラフ表示中にコミットをcheckout |
| Tree Scope | Gitグラフ表示範囲をLocal/Remote/Allで切替 |
| Checkout File | コミットファイル表示中にファイルをcheckout |
| Copy File | コミットファイル表示中にファイルをコピー |

#### Launch

| 項目 | 概要 |
| --- | --- |
| Launcher | `vfiler.def` の `launcher` / `luncher` コマンドを選択実行 |
| Setting Tool | `vfiler_setting.py` を起動し、終了後に設定を再読み込み |
| Full Screen Shell | 外部Shellを全画面で起動 |
| Run... | コマンド入力して実行 |
| New Text File... | テキストファイル作成 |
| New Archive... | zip/tar系アーカイブ作成 |
| 設定ランチャー | `vfiler.def` の `launcher` / `luncher` に定義した項目 |

### 機能一覧・概要

| 機能 | 概要 |
| --- | --- |
| ファイル一覧 | ディレクトリ、ファイル、dotfile、zipを色分け表示します。 |
| プレビュー | テキストファイル、zip/tar内容、ディレクトリ内容、検索結果周辺、Git差分などを右ペインに表示します。 |
| `thurupaths` 保護 | 指定ディレクトリは一覧取得やプレビューを `Y` 確認後に行います。1ペインのプレビューも `Y` を押すまで展開しません。 |
| 2ペイン操作 | ペイン移動、同期、コピー、移動、比較に使います。 |
| マーク操作 | 複数項目をマークしてコピー、移動、削除、Git操作などに渡します。 |
| ファイルクリップボード | `F9` / `Shift+F9` / `F10` でコピー、カット、貼り付けを行います。 |
| 検索 | 内容検索、ファイル名検索、検索結果からの編集やプレビューができます。 |
| フィルタ | 現在一覧を名前で絞り込みます。 |
| zip/tar操作 | アーカイブ内を一覧表示し、内容プレビュー、抽出、アーカイブ作成、アーカイブへの貼り付けができます。 |
| 外部コマンド | 拡張子別実行、ランチャー、任意コマンド実行、外部Shell起動ができます。 |
| Git操作 | ステータス、add、discard、ignore、履歴、グラフ、branch、commit、pull、pushなどを扱います。 |
| ログ | 操作ログ、外部コマンド出力、Tail結果を表示します。 |
| 常駐Shell連携 | Shellからポップアップ起動し、編集バッファ、ファイラー状態、ログを保持したままファイラー/エディタ/Shellを往復できます。 |
| Shell返却 | 常駐ファイラーで `Shift+Enter` を押すと選択項目をShell入力行へ返します。カレント内ならファイル名のみ、別ディレクトリなら絶対パスで返します。 |

## エディタ

### キー割当

| キー | 動作 |
| --- | --- |
| `F1` | Filesメニュー |
| `F2` | Editメニュー |
| `F3` | Settingsメニュー |
| `F4` | ファイラーへ戻る |
| `F5` | 画面分割を切替。単一、横分割、縦分割を巡回します。 |
| `F6` | 分割ペイン間を移動。Shell分割中はエディタペイン/Shellペインのフォーカス切替。 |
| `F7` | ペインサイズ変更 |
| `F8` | 通常選択のON/OFF |
| `Shift+F8` | 矩形選択のON/OFF |
| `F9` | コピー |
| `Shift+F9` | カット |
| `F10` | 貼り付け |
| `Shift+F10` | クリップ一覧 |
| `F11` | 通常モードではエディタ内Shellを開きます。常駐モードではShellへ戻ります。 |
| `Shift+F11` | 常駐モードでエディタ内Shellを開きます。 |
| `F12` | 次のバッファへ切替 |
| `Shift+F12` | バッファ一覧 |
| `Ctrl+S` | 保存 |
| `Ctrl+A` | 全選択 |
| `Ctrl+X` | カット |
| `Ctrl+C` | コピー |
| `Ctrl+V` | 貼り付け |
| `Ctrl+Shift+V` | クリップ一覧 |
| `Ctrl+F` | 検索 |
| `Ctrl+N` | 次を検索 |
| `Ctrl+Y` | 行削除 |
| `Ctrl+Z` | Undo |
| `Ctrl+R` | Redo |
| `Ctrl+W` | 単語削除 |
| `Ctrl+K` | 行末まで削除 |
| `Ctrl+L` | 計算ポップアップ。結果をカーソル位置へ挿入します。 |
| `ESC` / `Ctrl+Q` | 閉じる。未保存なら確認します。VIモードでは入力モードからコマンドモードへ戻ります。 |
| `e` / `E` | 読み取り専用表示中に編集モードへ入ります。 |
| `Insert` | Insert/Overwrite切替はSettingsメニューから行う旨を表示します。 |
| `↑` / `↓` / `←` / `→` | カーソル移動 |
| `Shift+↑` / `Shift+↓` / `Shift+←` / `Shift+→` | 選択しながら移動 |
| `Ctrl+←` | 行頭へ移動 |
| `Ctrl+→` | 行末へ移動 |
| `Ctrl+↑` | ファイル先頭へ移動 |
| `Ctrl+↓` | ファイル末尾へ移動 |
| `Home` | 行頭へ移動 |
| `End` | 行末へ移動 |
| `PageUp` | 1ページ上へ移動 |
| `PageDown` | 1ページ下へ移動 |
| `Enter` | 改行。読み取り専用時は閉じます。 |
| `Backspace` | 前方削除、選択範囲削除 |
| `Delete` | 後方削除、選択範囲削除 |
| `Tab` | インデント |
| `Shift+Tab` | アンインデント |
| マウスクリック | `Mouse Cursor` がONの場合、クリック位置へカーソル移動 |
| マウスホイール | `Wheel Scroll` がONの場合、スクロール |

エディタ内Shellペインにフォーカスがある場合、`Enter` はコマンド実行、`ESC` は入力クリアまたはShellフォーカス解除、`↑` / `↓` は履歴、`PageUp` / `PageDown` はShellログスクロールです。

### メニュー

#### Files

| 項目 | 概要 |
| --- | --- |
| Open | ファイル名を入力して開きます。 |
| New | `untitled.txt` の新規バッファを作成します。 |
| Save | 保存します。 |
| Save As | 別名保存します。 |
| Tail | 読み取り専用バッファで末尾追従を開始します。 |
| Close | バッファを閉じます。未保存なら確認します。 |

#### Edit

| 項目 | 概要 |
| --- | --- |
| Undo | 取り消し |
| Redo | やり直し |
| Cut | 選択範囲を切り取り |
| Copy | 選択範囲をコピー |
| Paste | クリップ内容を貼り付け |
| Clip List | クリップ履歴から貼り付け |
| Select All | 全選択 |
| Find | 検索 |
| Find Next | 次を検索 |
| Replace | 全行に対する文字列置換 |
| VI Mode | VI風操作モード切替 |
| Normalize EOL | 改行コードをOS標準へ正規化 |
| Delete Line | 行削除 |

#### Settings

| 項目 | 概要 |
| --- | --- |
| Tab Space | タブ幅を変更 |
| Wrap Mode | 折り返し/横スクロール切替 |
| Line Number | 行番号表示切替 |
| Mouse Cursor | マウスクリック移動切替 |
| Wheel Scroll | ホイールスクロール切替 |
| Ruler | ルーラー表示切替 |
| Cursor Underline | カーソル下線表示切替 |
| Show Enter | 改行記号表示切替 |
| Show Tab | タブ記号表示切替 |
| Show Bin | バイナリ表示切替 |
| Insert/Overwrite | 挿入/上書き切替 |
| Line Draw | 罫線描画モード |

#### Buffers

常駐モードまたは複数バッファ時に、開いているバッファ一覧を表示して切り替えます。未保存バッファには `*` が付きます。

### VIモード

Settingsメニューの `VI Mode` をONにすると、`ESC` でコマンドモードへ入り、以下の操作が使えます。

| キー/コマンド | 動作 |
| --- | --- |
| `i` | 挿入 |
| `a` | カーソル後に追記 |
| `h` / `j` / `k` / `l` | 移動 |
| `w` / `b` / `e` | 単語移動 |
| `0` | 行頭 |
| `G` | 最終行、または数値指定行 |
| `v` | ビジュアル選択 |
| `x` | 文字削除 |
| `d` + 移動 | 範囲削除 |
| `y` + 移動 | 範囲ヤンク |
| `c` + 移動 | 範囲削除後に挿入 |
| `p` | 貼り付け |
| `u` | Undo |
| `J` | 行結合 |
| `/` | 検索 |
| `n` | 次を検索 |
| `:w` | 保存 |
| `:q` | 閉じる |
| `:q!` | 破棄して閉じる |
| `:wq` | 保存して閉じる |
| `:s/old/new/` | 現在行の最初の一致を置換 |
| `:s/old/new/g` | 現在行の全一致を置換 |

### 機能一覧・概要

| 機能 | 概要 |
| --- | --- |
| 複数バッファ | 常駐モードでは編集バッファを保持し、Shell/ファイラー/エディタ間を往復できます。 |
| 保存/別名保存 | UTF-8等の検出結果を保持し、改行コードも保持します。 |
| 読み取り専用ビュー | `--v` やファイラーのViewから読み取り専用で開けます。 |
| Tail | 読み取り専用バッファでファイル末尾追従できます。 |
| 選択/矩形選択 | 通常選択と矩形選択を切り替え、コピー/カット/削除できます。 |
| クリップ履歴 | コピー/カットしたテキストを履歴として保持し、一覧から貼り付けできます。 |
| Undo/Redo | 最大100件のUndo履歴を持ちます。 |
| 検索/置換 | 検索履歴、次検索、文字列置換に対応します。 |
| 分割表示 | 横分割、縦分割、エディタ内Shellペインに対応します。 |
| 行番号/ルーラー/不可視文字 | 表示設定を切り替えられます。 |
| 構文色分け | `syntax` 設定により拡張子別のキーワード、コメント、文字列、数値、正規表現ハイライトを行います。 |
| VIモード | 最小限のVI風コマンド操作を提供します。 |
| 罫線描画 | Line Drawで罫線文字を描画できます。 |
| 計算貼り付け | `Ctrl+L` の計算ポップアップ結果を本文へ挿入できます。 |

## 設定ファイル

### 探索順

設定ファイルはJSONです。起動ディレクトリから順に以下を探します。

1. macOS/Linux: `vfiler.mac.def`、Windows cmd/PowerShell: `vfiler.win.shell.def`、Windows VS Code terminal: `vfiler.win.vscode.def`
2. `vfiler.def`
3. `vfiler.py` と同じディレクトリのプラットフォーム別def
4. `vfiler.py` と同じディレクトリの `vfiler.def`

見つからない場合は組み込み設定で動作します。

### トップレベル項目

| 項目 | 型 | 説明 |
| --- | --- | --- |
| `launcher` | 配列 | Launchメニューに追加する外部コマンド。 |
| `luncher` | 配列 | `launcher` と同じ扱い。既存互換の別名です。 |
| `exec` | 配列 | 拡張子別の実行コマンド。 |
| `directory` | 配列 | Dir Listに追加する移動先。 |
| `setting` | オブジェクト | 動作設定、色設定。 |
| `thurupaths` | 配列 | 一覧取得やプレビュー前に確認するディレクトリ。 |
| `syntax` | オブジェクト | 拡張子別の構文色分け。 |
| `windows.guards` | 配列 | Windowsで進入禁止にするパス。 |

`launcher` / `luncher` / `exec` / `directory` / `thurupaths` の各項目には、必要に応じて `os` を指定できます。

```json
{ "os": "mac" }
{ "os": ["mac", "linux"] }
```

`os` は `mac`、`linux`、`win` のいずれかです。省略時は全OSで有効です。

### `launcher` / `luncher`

Launchメニューへ外部コマンドを追加します。

```json
{
  "title": "Finder",
  "command": "open %p",
  "char": "UTF-8",
  "screen": "fullscreen",
  "os": "mac"
}
```

| キー | 説明 |
| --- | --- |
| `title` | メニュー表示名 |
| `command` | 実行コマンド |
| `char` | コマンド実行時の文字コード指定 |
| `screen` | `fullscreen` などの実行表示指定 |
| `os` | OS条件 |

### `exec`

拡張子別の実行コマンドを定義します。

```json
{
  "ext": "py",
  "command": "python3 %f",
  "os": ["mac", "linux"]
}
```

`ext` は先頭の `.` があってもなくても同じです。

### `directory`

Dir Listに移動先を追加します。

```json
{
  "title": "Filer Project",
  "command": "/path/to/project"
}
```

### コマンド展開

`launcher`、`exec`、任意コマンドの初期値などでは以下の置換が使えます。

| 記号 | 展開内容 |
| --- | --- |
| `%f` | 選択ファイル/ディレクトリのパス |
| `%b` | 選択項目の拡張子なしファイル名 |
| `%p` | 現在ペインのパス |
| `%ps` | 反対ペインのパス |
| `%*` | マーク項目、または選択項目の絶対パス一覧 |
| `%**` | マーク項目、または選択項目の現在ペイン基準相対パス一覧 |
| `${DATE}` | `YYYYMMDD` |
| `${TIME}` | `HHMM` |

パスは必要に応じてShell向けにクォートされます。

### `setting`

| キー | 値 | 説明 |
| --- | --- | --- |
| `editor` | 文字列 | 外部エディタ。未指定時はWindowsで `notepad %f`、macOS/Linuxで `vi %f`。 |
| `sh` | 文字列 | 外部Shell。未指定時は `$SHELL` または `/bin/sh`。 |
| `autosave_runlog` | `enable` など | ログの自動保存。 |
| `autosave_runlog_path` | 文字列 | 自動保存ログの保存先。 |
| `quit_prompt` | `true` / `enable` / `1` / `yes` / `on` | 終了確認を有効化。 |
| `show_ownerpath` | 同上 | 親ディレクトリ項目を表示。 |
| `change_file_datetime` | 同上 | コピー/移動時などの日時扱い設定。 |
| `diff_jump_before` | 数値 | 差分ジャンプ時に差分の前へ置く文脈行数。 |
| `painwidth` | 数値 | プレビュー/ペイン幅。パーセント指定で、30から80の範囲に丸められます。 |
| `dir_color` | 色 | ディレクトリ色。 |
| `dot_file_color` | 色 | dotfile色。 |
| `zip_file_color` | 色 | zip/tar等アーカイブ色。 |
| `file_color` | 色 | 通常ファイル色。 |
| `search_match_color` | 色 | 検索一致色。 |
| `editor_readonly_bar_color` | 色 | エディタ読み取り専用バー色。 |
| `editor_edit_bar_color` | 色 | エディタ編集バー色。 |
| `editor_lf_color` | 色 | LF表示色。 |
| `editor_cr_color` | 色 | CR表示色。 |
| `editor_crlf_color` | 色 | CRLF表示色。 |
| `editor_tab_color` | 色 | タブ表示色。 |
| `editor_bin_color` | 色 | バイナリ表示色。 |
| `filer_active_bar_color` | 色 | ファイラーのアクティブバー色。 |
| `log_prompt_color` | 色 | ログプロンプト色。 |
| `log_input_text_color` | 色 | ログ入力文字色。 |
| `log_input_existing_path_color` | 色 | ログ入力中の存在するパス色。 |
| `log_input_missing_path_color` | 色 | ログ入力中の存在しないパス色。 |
| `log_input_unclosed_string_color` | 色 | ログ入力中の未閉じクォート色。 |

真偽値として有効な文字列は `true`、`enable`、`1`、`yes`、`on` です。

色はANSI色名またはANSI SGR値を指定できます。例: `red`、`bright_cyan`、`default`、`none`、`30;43`。

### `thurupaths`

巨大ディレクトリなど、勝手に一覧取得やプレビューをしたくないパスを指定します。

```json
"thurupaths": [
  "/path/to/large-dir/",
  { "path": "/mnt/slow", "os": "linux" }
]
```

指定パスでは、一覧取得時に `get list? (N/y)` が表示されます。1ペインプレビューでも自動展開せず、`Y` を押した時だけディレクトリ内容を表示します。確認プロンプト中でも上下キーでカーソル移動できます。

### `syntax`

拡張子別に構文色分けを定義します。

```json
"syntax": {
  "py": {
    "keywords": ["def", "class", "import", "return"],
    "keyword_color": "cyan",
    "comment_color": "green",
    "string_color": "yellow",
    "number_color": "magenta"
  },
  "md": {
    "regex": [
      { "pattern": "^# .*$", "color": "bright_cyan" }
    ],
    "keywords": ["TODO", "FIXME"],
    "keyword_color": "bright_yellow",
    "comment_color": "gray",
    "string_color": "yellow",
    "number_color": "magenta"
  }
}
```

| キー | 説明 |
| --- | --- |
| `keywords` | キーワード配列。単語として一致した箇所を色付けします。 |
| `regex` | `{ "pattern": "...", "color": "..." }` の配列。正規表現に一致した行/部分を色付けします。 |
| `keyword_color` | キーワード色 |
| `comment_color` | コメント色 |
| `string_color` | 文字列色 |
| `number_color` | 数値色 |

組み込みでは `py`、`json`、`md`、`markdown` の基本ルールがあります。設定ファイルで同じ拡張子を指定すると上書き/追加されます。

### 状態保存ファイル

`--nostat` を付けない場合、表示状態やエディタ設定などは `vfiler_stat.json` に保存されます。保存対象には、ペイン位置、モード、折り返し、行番号、日時表示、マウス設定、ルーラー、VIモード、ブックマーク、検索履歴、置換履歴などがあります。
