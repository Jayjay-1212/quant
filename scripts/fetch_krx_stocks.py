"""KRX 전체 종목 리스트 수집 스크립트

수집 우선순위:
1. FinanceDataReader StockListing('KRX')
2. FinanceDataReader StockListing('KOSPI') + StockListing('KOSDAQ') 개별 시도
3. KIND (kind.krx.co.kr) 종목 리스트 다운로드 (HTML table)

결과: data/krx_stocks.csv (Code, Name, Market, MarketCap)
MarketCap은 원(won) 단위. KIND 소스에서는 시총 정보 없어 0으로 저장.
"""

import os
import sys
import time
import warnings
from io import StringIO

import requests
import pandas as pd

warnings.filterwarnings('ignore', category=FutureWarning)

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'krx_stocks.csv')


def try_fdr_krx():
    """방법 1: FinanceDataReader StockListing('KRX')"""
    print("[1/3] FinanceDataReader StockListing('KRX') 시도...")
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing('KRX')
        if df is not None and len(df) > 0:
            print(f"  -> 성공! {len(df)}개 종목 수집")
            return _normalize_fdr(df, market_col_guess=True)
    except Exception as e:
        print(f"  -> 실패: {e}")
    return None


def try_fdr_separate():
    """방법 2: KOSPI + KOSDAQ 개별 수집"""
    print("[2/3] FinanceDataReader KOSPI + KOSDAQ 개별 시도...")
    frames = []
    try:
        import FinanceDataReader as fdr
        for market in ('KOSPI', 'KOSDAQ'):
            try:
                df = fdr.StockListing(market)
                if df is not None and len(df) > 0:
                    df = _normalize_fdr(df, market_col_guess=False)
                    df['Market'] = market
                    frames.append(df)
                    print(f"  -> {market}: {len(df)}개 종목")
                else:
                    print(f"  -> {market}: 데이터 없음")
            except Exception as e:
                print(f"  -> {market} 실패: {e}")
            time.sleep(1)

        if frames:
            result = pd.concat(frames, ignore_index=True)
            print(f"  -> 총 {len(result)}개 종목 수집")
            return result
    except ImportError:
        print("  -> FinanceDataReader 미설치")
    return None


def try_kind_direct():
    """방법 3: KIND (kind.krx.co.kr) 에서 종목 리스트 다운로드"""
    print("[3/3] KIND 웹사이트 직접 요청...")
    frames = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
    }

    market_types = [
        ('stockMkt', 'KOSPI'),
        ('kosdaqMkt', 'KOSDAQ'),
    ]

    for mkt_type, mkt_name in market_types:
        try:
            url = 'https://kind.krx.co.kr/corpgeneral/corpList.do'
            params = {'method': 'download', 'marketType': mkt_type}
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            resp.raise_for_status()

            # KIND returns HTML table with euc-kr encoding
            dfs = pd.read_html(StringIO(resp.text), encoding='euc-kr')
            if not dfs or len(dfs[0]) == 0:
                print(f"  -> {mkt_name}: 데이터 없음")
                continue

            df = dfs[0]
            cols = df.columns.tolist()

            # KIND columns (Korean): 회사명, 종목코드, 업종, etc.
            # Find code and name columns by position (reliable)
            # Column order: 회사명, 종목구분, 종목코드, 업종, ...
            result = pd.DataFrame()

            # 종목코드 is typically the 3rd column (index 2)
            code_col = None
            name_col = None
            for i, col in enumerate(cols):
                col_str = str(col)
                if '코드' in col_str:
                    code_col = col
                elif '회사명' in col_str or '종목명' in col_str:
                    name_col = col

            # Fallback: use first two columns
            if name_col is None:
                name_col = cols[0]
            if code_col is None:
                code_col = cols[2] if len(cols) > 2 else cols[1]

            result['Code'] = df[code_col].astype(str).str.strip().str.zfill(6)
            result['Name'] = df[name_col].astype(str).str.strip()
            result['Market'] = mkt_name
            result['MarketCap'] = 0  # KIND doesn't provide market cap

            # Filter out rows with invalid codes (non-numeric)
            result = result[result['Code'].str.match(r'^\d{6}$')]

            frames.append(result)
            print(f"  -> {mkt_name}: {len(result)}개 종목")

        except Exception as e:
            print(f"  -> {mkt_name} 실패: {e}")

        time.sleep(1)

    if frames:
        result = pd.concat(frames, ignore_index=True)
        print(f"  -> 총 {len(result)}개 종목 수집")
        return result
    return None


def _normalize_fdr(df, market_col_guess=False):
    """FinanceDataReader 결과를 표준 형식으로 변환"""
    result = pd.DataFrame()
    cols = df.columns.tolist()

    # Code
    if 'Code' in cols:
        result['Code'] = df['Code'].astype(str).str.strip().str.zfill(6)
    elif 'Symbol' in cols:
        result['Code'] = df['Symbol'].astype(str).str.strip().str.zfill(6)
    elif 'Ticker' in cols:
        result['Code'] = df['Ticker'].astype(str).str.strip().str.zfill(6)
    else:
        return None

    # Name
    if 'Name' in cols:
        result['Name'] = df['Name'].astype(str).str.strip()
    else:
        return None

    # Market
    if 'Market' in cols:
        result['Market'] = df['Market'].astype(str).str.strip()
    elif market_col_guess:
        result['Market'] = 'KRX'
    else:
        result['Market'] = 'KRX'

    # MarketCap (원 단위)
    if 'Marcap' in cols:
        result['MarketCap'] = pd.to_numeric(df['Marcap'], errors='coerce').fillna(0).astype(int)
    elif 'MarketCap' in cols:
        result['MarketCap'] = pd.to_numeric(df['MarketCap'], errors='coerce').fillna(0).astype(int)
    else:
        result['MarketCap'] = 0

    return result


def main():
    print("=" * 60)
    print("KRX 전체 종목 리스트 수집")
    print("=" * 60)

    # 순차적으로 시도
    df = try_fdr_krx()

    if df is None:
        df = try_fdr_separate()

    if df is None:
        df = try_kind_direct()

    if df is None or len(df) == 0:
        print("\n모든 방법 실패. 종목 리스트를 수집할 수 없습니다.")
        sys.exit(1)

    # 중복 제거 (Code 기준)
    df = df.drop_duplicates(subset='Code', keep='first').reset_index(drop=True)

    # MarketCap 내림차순 정렬
    df = df.sort_values('MarketCap', ascending=False).reset_index(drop=True)

    # 저장
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

    print(f"\n저장 완료: {OUTPUT_PATH}")
    print(f"총 종목 수: {len(df)}")
    print(f"컬럼: {list(df.columns)}")
    print(f"\n상위 10개:")
    top10 = df.head(10)
    for _, row in top10.iterrows():
        mcap_조 = row['MarketCap'] / 1_000_000_000_000 if row['MarketCap'] > 0 else 0
        mcap_str = f"{mcap_조:8.1f}조원" if mcap_조 > 0 else "   N/A"
        print(f"  {row['Code']} {row['Name']:20s} {row['Market']:8s} {mcap_str}")

    print(f"\nKOSPI: {len(df[df['Market'] == 'KOSPI'])}개")
    print(f"KOSDAQ: {len(df[df['Market'] == 'KOSDAQ'])}개")
    other_count = len(df[~df['Market'].isin(['KOSPI', 'KOSDAQ'])])
    if other_count > 0:
        print(f"기타: {other_count}개")


if __name__ == '__main__':
    main()
