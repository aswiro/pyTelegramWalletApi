import hashlib
import time
import uuid

import requests

from wallet.types import Offer, Balances, BalanceAccount, TxResponse, TxDetails, Order, MarketOffer


class Wallet:
    def __init__(self, auth_token: str, log_response=False, token_file_path=None):
        self.token_file_path = token_file_path
        self.log_response = log_response
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers = {
            'content-type': 'application/json',
        }

        self.endpoint = 'https://walletbot.me'

        if auth_token == '' or len(auth_token) < 30:
            raise Exception('[!] Bad auth token!')

    @staticmethod
    def token_from_file(path, log_response=False):
        with open(path, 'r') as f:
            auth_token = f.read()
        return Wallet(auth_token, log_response, token_file_path=path)

    def update_token(self):
        """ For dynamically token update from "token_file_path"

        :return:
        """
        if self.token_file_path is None:
            raise Exception('[!] token_file_path not set!')
        with open(self.token_file_path, 'r') as f:
            self.auth_token = f.read()

    def request(self, path: str, api_version: str = "api/v1", method: str = "GET", json_data=None, params=None,
                max_attempts=3):

        public_apis = ['p2p/public-api/v2', 'users/public-api/v2', 'rates/public-api/v1']

        if api_version in public_apis or api_version == 'v2api':
            self.session.headers['authorization'] = 'Bearer ' + self.auth_token
        else:
            self.session.headers['authorization'] = self.auth_token

        url = f"{self.endpoint}/{api_version}/{path}"

        counter = 0
        while counter < max_attempts:
            counter += 1
            try:
                response = self.session.request(method, url, json=json_data, params=params, timeout=10)
                status_code = response.status_code

                if status_code == 200:
                    if self.log_response:
                        print(response.text)
                    jdata = response.json()
                    if api_version in public_apis:
                        if jdata['status'] == 'SUCCESS':
                            if 'data' in jdata:
                                return jdata['data']
                            else:
                                return True
                        else:
                            raise Exception(f'Bad request status: {jdata["status"]}')
                    else:
                        return jdata
                elif status_code == 401 or status_code == 400:
                    print(response.text)
                    raise Exception(f'API TOKEN EXPIRED')
                elif status_code == 429:
                    raise Exception('You are Rate Limited')
                else:
                    raise Exception(f'REQ STATUS CODE: {status_code}')

            except Exception as e:
                print(f'[!] Request error: {e}. Try attempt #{counter}')
                time.sleep(2)

        raise Exception('[!] Request attempts end')

    def get_earn_campings(self):
        return self.request('earn/campaigns', 'v2api')

    def get_user_balances(self, currency: str = None) -> Balances | BalanceAccount:
        """ Account balances

        :param currency: TON NOT BTC USDT
        :return:
        """
        balances: Balances = Balances.from_dict(self.request(f'accounts/'))
        if currency:
            for a in balances.accounts:
                if a.currency == currency:
                    return a
        else:
            return balances

    def get_transactions(self, limit: int = 20, last_id: int = None, crypto_currency: str = None,
                         transaction_type: str = None, transaction_gateway: str = None) -> list[TxDetails]:
        """ Account in withdraw | deposit txs

        :param transaction_gateway: withdraw_onchain | tg_transfer | top_up | p2p_order | earn | internal
        :param transaction_type: withdraw | deposit
        :param crypto_currency: BTC USDT TON NOT
        :param limit:
        :param last_id:
        :return:
        """
        params = {
            'limit': limit,
            'last_id': last_id,
            'crypto_currency': crypto_currency,
            'transaction_type': transaction_type,
            'transaction_gateway': transaction_gateway
        }
        return TxResponse.from_dict(self.request(f'transactions/', params=params)).transactions

    def get_transaction_details(self, tx_id: int) -> TxDetails:
        """ One tx info

        :param tx_id:
        :return:
        """

        return TxDetails.from_dict(self.request(f'transactions/details/{tx_id}/'))

    def get_passcode_info(self) -> dict:
        return self.request(f'passcode/info', api_version='v2api')

    def get_recovery_email(self, product: str):
        """

        :param product: wallet | ton-space
        :return:
        """
        params = {'product': product}
        return self.request(f'recovery-email/', api_version='v2api', params=params)

    def get_user_region_verification(self) -> dict:
        return self.request('region-verification/status', api_version='users/public-api/v2')

    def get_wallet(self, crypto_currency: str) -> list:
        """ Get address your wallet to deposit

        :param crypto_currency: TON
        :return:
        """
        return self.request(f'users/get_or_create_wallets/{crypto_currency}')

    def get_exchange_pair_info(self, from_currency: str, to_currency=str, from_amount: float = 1) -> dict:
        """

        :param from_currency: BTC USDT TON NOT
        :param to_currency: BTC USDT TON NOT
        :param from_amount:
        :return:
        """
        data = {
            "from_amount": from_amount,
            "from_currency": from_currency,
            "to_currency": to_currency
        }
        return self.request('exchange/convert/', method='POST', json_data=data)

    def get_available_exchanges(self):
        """
            https://walletbot.me/api/v1/exchange/get-available-exchanges/
            GET
        """
        raise Exception('Not realized')

    # P2P Market

    def get_own_p2p_user_info(self):
        data = {'deviceId': hashlib.md5(uuid.UUID(int=uuid.getnode()).hex.encode('utf-8')).hexdigest()[:20]}
        return self.request('user/get', api_version='users/public-api/v2', method='POST', json_data=data)

    def get_user_p2p_payments(self) -> dict:
        """ List own payment methods

        :return:
        """
        return self.request('payment-details/get/by-user-id', api_version='p2p/public-api/v2', method='POST')

    def get_supported_p2p_fiat(self):
        """
            https://walletbot.me/p2p/public-api/v2/currency/all-supported-fiat
            POST
        """
        raise Exception('Not realized')

    def get_offer_settings(self):
        """
            https://walletbot.me/p2p/public-api/v2/offer/settings/get
            POST
        """
        raise Exception('Not realized')

    def get_own_p2p_order_history(self, offset=0, limit=20, status: str = 'ALL_ACTIVE') -> list[Order]:
        """

        :param offset:
        :param limit:
        :param status: ALL_ACTIVE | ALL_COMPLETED
        :return:
        """
        data = {
            "offset": offset,
            "limit": limit,
            "filter": {
                "status": status
            }
        }
        orders_raw = self.request(
            'offer/order/get-history/by-user-id',
            method='POST',
            api_version='p2p/public-api/v2',
            json_data=data)

        return [Order.from_dict(o) for o in orders_raw]

    def get_p2p_order(self, order_id: int):
        """ Order - its active or completed offer

        :param order_id:
        :return:
        """
        data = {'orderId': order_id}
        return Order.from_dict(
            self.request('offer/order/get', api_version='p2p/public-api/v2', method='POST', json_data=data))

    def get_p2p_rate(self, base='TON', quote='RUB') -> dict:
        params = {'base': base, 'quote': quote}
        return self.request(f'rate/crypto-to-fiat', api_version='rates/public-api/v1', params=params)

    def get_p2p_price_limits(self):
        """
        https://walletbot.me/p2p/public-api/v2/offer/limits/fixed-price/get
        POST
        {
            "baseCurrencyCode": "TON",
            "quoteCurrencyCode": "RUB"
        }

        :return:
        """
        raise Exception('Not realized')

    def get_p2p_payment_methods_by_currency(self, currency='RUB') -> dict:
        data = {"currencyCode": currency}
        return self.request(
            'payment-details/get-methods/by-currency-code',
            api_version='p2p/public-api/v2',
            method='POST',
            json_data=data)

    def create_p2p_offer(self, currency: str, amount: float, fiat: str, margine: int, offer_type: str,
                         order_min_price: int, pay_methods: list, comment: str = None, price_type: str = "FLOATING",
                         confirm_timeout_tag: str = "PT15M") -> Offer:
        """

        :param pay_methods: list of payment methods ids or list of payment methods codes
            if SALE - get_user_p2p_payments()
            if PURCHASE - get_p2p_payment_methods_by_currency()

        :param confirm_timeout_tag: PT15M PT5M PT10M
        :param comment:
        :param order_min_price:
        :param margine: 90 - 120
        :param fiat: RUB | KZT etc...
        :param price_type: FLOATING | FIXED
        :param amount:
        :param currency: TON | BTC
        :param offer_type:  SALE | PURCHASE
        :return:
        """

        data = {
            "type": offer_type,
            "initVolume": {
                "currencyCode": currency,
                "amount": str(amount)
            },
            "price": {
                "type": price_type,
                "baseCurrencyCode": currency,
                "quoteCurrencyCode": fiat,
                "value": margine
            },
            "orderAmountLimits": {
                "min": order_min_price
            },
            "paymentConfirmTimeout": confirm_timeout_tag,
            "comment": comment,
        }

        if offer_type == 'PURCHASE':
            data['paymentMethodCodes'] = pay_methods
        else:
            data['paymentDetailsIds'] = pay_methods

        return Offer.from_dict(
            self.request('offer/create', api_version='p2p/public-api/v2', method='POST', json_data=data))

    def activate_p2p_offer(self, offer_id, offer_type):
        data = {"type": offer_type, "offerId": offer_id}
        return self.request('offer/activate', api_version='p2p/public-api/v2', method='POST', json_data=data)

    def deactivate_p2p_offer(self, offer_id, offer_type):
        data = {
            "type": offer_type,
            "offerId": offer_id
        }
        return self.request('offer/deactivate', api_version='p2p/public-api/v2', method='POST', json_data=data)

    def disable_p2p_bidding(self):
        return self.request('user-settings/disable-bidding', api_version='p2p/public-api/v2', method='POST')

    def enable_p2p_bidding(self):
        return self.request('user-settings/enable-bidding', api_version='p2p/public-api/v2', method='POST')

    def get_own_p2p_offers(self, offset: int = 0, limit: int = 10,
                           offer_type: str = 'PURCHASE', status: str | None = None) -> list[Offer]:
        """
        :param offset:
        :param limit: None | PURCHASE | SALE
        :param offer_type:
        :param status: None | ACTIVE | INACTIVE
        :return:
        """
        data = {
            "offset": offset,
            "limit": limit,
            "offerType": offer_type
        }
        raw_offers = self.request(
            'offer/user-own/list', api_version='p2p/public-api/v2', method='POST', json_data=data)

        offers = [Offer.from_dict(o) for o in raw_offers]

        if status is not None:
            offers = [Offer.from_dict(o) for o in raw_offers if o['status'] == status]

        return offers

    def get_own_p2p_offer(self, offer_id: int) -> Offer:
        json_data = {"offerId": offer_id}
        return Offer.from_dict(self.request(
            'offer/get-user-own', api_version='p2p/public-api/v2', method='POST', json_data=json_data))

    def get_p2p_offer(self, offer_id: int) -> Offer:
        data = {"offerId": offer_id}
        return Offer.from_dict(
            self.request('offer/get', api_version='p2p/public-api/v2', method='POST', json_data=data))

    def edit_p2p_offer(self, offer_id: int, margine: int = None, volume: float = None,
                       order_amount_min: float = None, comment: str = None):
        """

        :param margine:
        :param comment:
        :param order_amount_min:
        :param volume:
        :param offer_id:
        :return:
        """
        offer = self.get_p2p_offer(offer_id)

        data = {
            "offerId": offer_id,
            "paymentConfirmTimeout": offer.paymentConfirmTimeout,
            "type": offer.type,
            "price": {
                "type": offer.price.type,
                "value": offer.price.value
            },
            "orderAmountLimits": {
                "min": offer.orderAmountLimits.min
            },
            "comment": offer.comment,
            "volume": 5,
        }

        if margine:
            data['price']['value'] = margine

        if volume:
            data['volume'] = volume

        if order_amount_min:
            data['orderAmountLimits']['min'] = order_amount_min

        if comment:
            data['comment'] = comment

        return Offer.from_dict(
            self.request('offer/edit', api_version='p2p/public-api/v2', method='POST', json_data=data))

    def accept_p2p_order(self, order_id: int, offer_type: str) -> Order:
        """

        :param order_id:
        :param offer_type: SALE | PURCHASE
        :return:
        """
        data = {
            'orderId': order_id,
            'type': offer_type,
        }
        return Order.from_dict(
            self.request('offer/order/accept', api_version='p2p/public-api/v2', method='POST', json_data=data))

    def get_p2p_market(self, base_currency_code: str, quote_currency_code: str, offer_type='SALE', offset=0, limit=100,
                       desired_amount=None) -> list[MarketOffer]:
        """

        :param desired_amount:
        :param base_currency_code: TON | BTC
        :param quote_currency_code: RUB | KZT etc.
        :param offer_type: SALE | PURCHASE
        :param offset:
        :param limit:
        :return:
        """
        data = {
            "baseCurrencyCode": base_currency_code,
            "quoteCurrencyCode": quote_currency_code,
            "offerType": offer_type,
            "offset": offset,
            "limit": limit,
            "desiredAmount": desired_amount
        }
        market = self.request(
            'offer/depth-of-market', api_version='p2p/public-api/v2', method='POST', json_data=data)
        return [MarketOffer.from_dict(offer) for offer in market]

    def send_to_address(self, amount, currency, address, network=None):
        """

        :param network: for USDT - ton | tron
        :param amount:
        :param currency:
        :param address:
        :return: dict {'transaction_id': 000000}
        """

        if currency == 'USDT' and not network:
            raise Exception('NETWORK NOT SET | For USDT set network="ton" or network="tron"')

        validate = self.withdrawals_validate_amount(amount, currency, address=address, network=network)
        if validate['status'] == 'OK':
            withdraw_request = self._create_withdraw_request(amount, currency, address, network)
            return self._process_withdraw_request(withdraw_request['uid'])
        else:
            raise Exception(f'[!] Bad validate status: {validate}')

    def _process_withdraw_request(self, uid):
        return self.request(f'withdrawals/process_withdraw_request/{uid}/', method='POST')

    def withdrawals_validate_amount(self, amount: float, currency: str, receiver_tg_id: int = None,
                                    address: str = None, network: str = None):
        params = {
            'amount': amount,
            'currency': currency,
            'receiver_tg_id': receiver_tg_id,
            'address': address,
            'network': network.lower() if network else None
        }
        return self.request(f'withdrawals/validate_amount/', params=params)

    def _create_withdraw_request(self, amount: float, currency: str, address: str, network: str):
        params = {
            'amount': str(amount),
            'currency': currency,
            'max_value': 'false',
            'address': address,
            "network": network
        }
        return self.request('withdrawals/create_withdraw_request/', method='POST', params=params)

    def process_transfer(self, tx_id: str):
        return self.request(f'transfers/process_transfer/{tx_id}/', method='POST')

    def send_to_user(self, amount, currency, receiver_tg_id):
        v = self.withdrawals_validate_amount(amount, currency, receiver_tg_id)

        if v['status'] == 'OK':
            data = {
                'amount': amount,
                'currency': currency
            }
            tx = self.request(
                f'transfers/create_transfer_request/', method='POST', json_data=data)['transfer_request_id']

            return self.process_transfer(tx)

        else:
            raise Exception(f'[!] Error withdrawals_validate_amount: {v}')
