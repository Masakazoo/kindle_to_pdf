import sys
import subprocess
from .converter import KindleToPDF

def main():
    """メイン関数"""
    print("=" * 60)
    print("Kindle to PDF Converter")
    print("=" * 60)
    
    # 設定
    default_book_name = "kindle_book"
    book_name = input(f"📖 書籍名 [{default_book_name}]: ").strip()
    if not book_name:
        book_name = default_book_name
    
    # ページ数入力（デフォルト100）
    default_pages = 100
    try:
        page_input = input(f"📖 総ページ数 [{default_pages}]: ").strip()
        if not page_input:
            total_pages = default_pages
        else:
            total_pages = int(page_input)
            if total_pages <= 0:
                raise ValueError
    except ValueError:
        print("❌ 有効なページ数を入力してください")
        sys.exit(1)
        
    print(f"   -> {total_pages}ページ を処理します")
    
    # めくり方向選択
    print("📖 ページめくり方向:")
    print("1: 左開き (横書き) [→キー] (デフォルト)")
    print("2: 右開き (縦書き) [←キー]")
    direction_input = input("選択 [1]: ").strip()
    
    page_turn_direction = 'right' if direction_input == '2' else 'left'
    direction_str = "右開き(←)" if page_turn_direction == 'right' else "左開き(→)"
    print(f"   -> {direction_str} で処理します")
    
    print()
    print("⚠️ 重要な準備:")
    print("1. Kindle for Macで対象の書籍を開いてください")
    print("2. 全画面表示を解除し、ウィンドウサイズを調整してください")
    print("3. 最初のページ（読み始めるページ）を表示してください")
    print("4. 他のウィンドウを最小化してください")
    print()
    
    input("準備ができたらEnterキーを押してください...")
    print()
    
    # 処理実行
    converter = KindleToPDF(book_name, total_pages, page_turn_direction)
    pdf_path = converter.run()
    
    if pdf_path:
        # Finderで出力先を開く
        subprocess.run(['open', str(pdf_path.parent)])
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
