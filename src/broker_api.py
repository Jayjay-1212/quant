import os
import json
import requests
from datetime import datetime


class KISBroker:
    """한국투자증권 KIS Developers Open API 연동

    .env 파일에 아래 항목 필요:
        KIS_APP_KEY=your_app_key
        KIS_APP_SECRET=your_app_secret
        KIS_ACCOUNT_NO=your_account_number (8자리-2자리)
        KIS_MOCK=true  (모의투자: true, 실전: false)
    """

    REAL_URL = "https://openapi.koreainvestment.com:9443"
    MOCK_URL = "https://openapivts.koreainvestment.com:29443"

    def __init__(self):
        self._load_env()
        self.is_mock = os.getenv('KIS_MOCK', 'true').lower() == 'true'
        self.base_url = self.MOCK_URL if self.is_mock else self.REAL_URL
        self.app_key = os.getenv('KIS_APP_KEY', '')
        self.app_secret = os.getenv('KIS_APP_SECRET', '')
        self.account_no = os.getenv('KIS_ACCOUNT_NO', '')
        self.access_token = None
        self.token_expired_at = None

        if not self.app_key or not self.app_secret:
            print("[WARN] KIS API credentials not found in .env")
            print("       Create .env file with KIS_APP_KEY and KIS_APP_SECRET")

    def _load_env(self):
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if not os.path.exists(env_path):
            return
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    def _get_account_parts(self):
        parts = self.account_no.split('-')
        if len(parts) == 2:
            return parts[0], parts[1]
        return self.account_no[:8], self.account_no[8:10]

    def authenticate(self):
        """OAuth 접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        resp = requests.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

        self.access_token = data['access_token']
        self.token_expired_at = data.get('access_token_token_expired', '')
        print(f"[AUTH] Token issued. Expires: {self.token_expired_at}")
        return self.access_token

    def _headers(self, tr_id):
        """공통 헤더 생성"""
        if not self.access_token:
            self.authenticate()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }

    def get_balance(self):
        """잔고 조회 (보유 종목 + 예수금)"""
        tr_id = "VTTC8434R" if self.is_mock else "TTTC8434R"
        cano, acnt_prdt_cd = self._get_account_parts()

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        resp = requests.get(url, headers=self._headers(tr_id), params=params)
        resp.raise_for_status()
        data = resp.json()

        holdings = []
        for item in data.get('output1', []):
            if int(item.get('hldg_qty', 0)) > 0:
                holdings.append({
                    'ticker': item['pdno'],
                    'name': item['prdt_name'],
                    'qty': int(item['hldg_qty']),
                    'avg_price': float(item['pchs_avg_pric']),
                    'current_price': float(item['prpr']),
                    'eval_amount': float(item['evlu_amt']),
                    'profit_pct': float(item['evlu_pfls_rt']),
                })

        summary = data.get('output2', [{}])[0] if data.get('output2') else {}

        return {
            'holdings': holdings,
            'total_eval': float(summary.get('tot_evlu_amt', 0)),
            'deposit': float(summary.get('dnca_tot_amt', 0)),
            'total_profit': float(summary.get('evlu_pfls_smtl_amt', 0)),
            'total_profit_pct': float(summary.get('tot_evlu_pfls_rt', 0)),
        }

    def order_market(self, ticker, qty, side='buy'):
        """시장가 주문

        Args:
            ticker: 종목코드 (예: '005930')
            qty: 주문 수량
            side: 'buy' or 'sell'
        """
        if side == 'buy':
            tr_id = "VTTC0802U" if self.is_mock else "TTTC0802U"
        else:
            tr_id = "VTTC0801U" if self.is_mock else "TTTC0801U"

        cano, acnt_prdt_cd = self._get_account_parts()

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": ticker,
            "ORD_DVSN": "01",  # 시장가
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",   # 시장가는 0
        }

        resp = requests.post(url, headers=self._headers(tr_id), json=body)
        resp.raise_for_status()
        data = resp.json()

        success = data.get('rt_cd') == '0'
        return {
            'success': success,
            'message': data.get('msg1', ''),
            'order_no': data.get('output', {}).get('ODNO', ''),
            'ticker': ticker,
            'side': side,
            'qty': qty,
            'timestamp': datetime.now().isoformat(),
        }

    def print_balance(self, balance=None):
        if balance is None:
            balance = self.get_balance()

        mode = "MOCK" if self.is_mock else "REAL"
        print(f"\n{'=' * 60}")
        print(f"  KIS Balance [{mode}]")
        print(f"{'=' * 60}")
        print(f"  Deposit:       {balance['deposit']:>16,.0f}")
        print(f"  Total Eval:    {balance['total_eval']:>16,.0f}")
        print(f"  Total Profit:  {balance['total_profit']:>16,.0f} "
              f"({balance['total_profit_pct']:.2f}%)")
        print(f"{'-' * 60}")

        for h in balance['holdings']:
            print(f"  {h['ticker']} {h['name'][:10]:<10s} "
                  f"Qty:{h['qty']:>6d}  "
                  f"Avg:{h['avg_price']:>10,.0f}  "
                  f"Now:{h['current_price']:>10,.0f}  "
                  f"P/L:{h['profit_pct']:>+.2f}%")
        print(f"{'=' * 60}")
