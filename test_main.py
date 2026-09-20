import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import os

# Mock env vars before importing bot
os.environ['TARGET_WALLET_ADDRESS'] = '0x1234567890123456789012345678901234567890'
os.environ['ETH_RPC_URL'] = 'http://mock.eth.rpc'
os.environ['BASE_RPC_URL'] = 'http://mock.base.rpc'

import main as bot
from main import poll_once
import telegram_utils

class TestBot(unittest.TestCase):

    @patch('telegram_utils.requests.post')
    def test_send_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        telegram_utils._send_message('dummy_token', 'dummy_chat', 'test message')
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['text'], 'test message')
        self.assertEqual(kwargs['json']['chat_id'], 'dummy_chat')

    @patch('main.send_log')
    @patch('main.send_deposit_notification')
    @patch('web3.eth.Eth.block_number', new_callable=PropertyMock)
    def test_poll_once_no_new_blocks(self, mock_block_number, mock_send_deposit, mock_send_log):
        mock_block_number.side_effect = [100, 200]
        new_eth, new_base = poll_once(100, 200)

        self.assertEqual(new_eth, 100)
        self.assertEqual(new_base, 200)
        mock_send_deposit.assert_not_called()

    @patch('main.send_log')
    @patch('main.send_deposit_notification')
    @patch('web3.eth.Eth.block_number', new_callable=PropertyMock)
    def test_poll_once_new_blocks_no_deposits(self, mock_block_number, mock_send_deposit, mock_send_log):
        mock_block_number.side_effect = [105, 205]
        
        bot.eth_usdc_contract.events.Transfer.get_logs = MagicMock(return_value=[])
        bot.base_usdc_contract.events.Transfer.get_logs = MagicMock(return_value=[])

        new_eth, new_base = poll_once(100, 200)

        self.assertEqual(new_eth, 105)
        self.assertEqual(new_base, 205)
        mock_send_deposit.assert_not_called()
        # Should have logged the block scanning twice
        self.assertEqual(mock_send_log.call_count, 2)

    @patch('main.send_log')
    @patch('main.send_deposit_notification')
    @patch('web3.eth.Eth.block_number', new_callable=PropertyMock)
    def test_poll_once_new_blocks_with_deposit(self, mock_block_number, mock_send_deposit, mock_send_log):
        mock_block_number.side_effect = [105, 200]
        
        mock_event = MagicMock()
        mock_event.args.to = bot.target_wallet
        mock_event.args.value = 5000000 # 5 USDC
        
        bot.eth_usdc_contract.events.Transfer.get_logs = MagicMock(return_value=[mock_event])
        bot.base_usdc_contract.events.Transfer.get_logs = MagicMock(return_value=[])

        new_eth, new_base = poll_once(100, 200)

        self.assertEqual(new_eth, 105)
        mock_send_deposit.assert_called_once()
        # Verify the raw message part of the call
        args, kwargs = mock_send_deposit.call_args
        self.assertIn("USDC DEPOSIT DETECTED: 5.0 USDC on Ethereum", args[1])

    @patch('main.send_log')
    @patch('main.send_error_notification')
    @patch('web3.eth.Eth.block_number', new_callable=PropertyMock)
    def test_poll_once_rpc_error(self, mock_block_number, mock_send_error, mock_send_log):
        mock_block_number.side_effect = [105, 200]
        
        bot.eth_usdc_contract.events.Transfer.get_logs = MagicMock(side_effect=Exception("RPC timeout"))
        bot.base_usdc_contract.events.Transfer.get_logs = MagicMock(return_value=[])

        new_eth, new_base = poll_once(100, 200)

        self.assertEqual(new_eth, 100) # Block not updated on failure
        mock_send_error.assert_called_once()

if __name__ == '__main__':
    unittest.main()
