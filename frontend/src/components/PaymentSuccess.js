import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const PaymentSuccess = () => {
  const [status, setStatus] = useState('checking'); // checking, success, error
  const [paymentDetails, setPaymentDetails] = useState(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const sessionId = getUrlParameter('session_id');
    if (sessionId) {
      pollPaymentStatus(sessionId);
    } else {
      setStatus('error');
    }
  }, []);

  const getUrlParameter = (name) => {
    name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
    const regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
    const results = regex.exec(window.location.search);
    return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
  };

  const pollPaymentStatus = async (sessionId, currentAttempts = 0) => {
    const maxAttempts = 10;
    const pollInterval = 2000; // 2 seconds

    if (currentAttempts >= maxAttempts) {
      setStatus('error');
      return;
    }

    try {
      const token = localStorage.getItem('storm_oracle_token');
      if (!token) {
        setStatus('error');
        return;
      }

      const response = await axios.get(
        `${API}/api/payments/checkout/status/${sessionId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      const data = response.data;
      
      if (data.payment_status === 'paid') {
        setPaymentDetails(data);
        setStatus('success');
        return;
      } else if (data.status === 'expired') {
        setStatus('error');
        return;
      }

      // If payment is still pending, continue polling
      setAttempts(currentAttempts + 1);
      setTimeout(() => pollPaymentStatus(sessionId, currentAttempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setStatus('error');
    }
  };

  const handleContinue = () => {
    window.location.href = '/';
  };

  const handleViewAccount = () => {
    window.location.href = '/account';
  };

  if (status === 'checking') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-slate-800/95 border-slate-700">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4">
              <Loader2 className="h-12 w-12 text-blue-400 animate-spin" />
            </div>
            <CardTitle className="text-white">Processing Payment</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-slate-300">
              We're verifying your payment with Stripe...
            </p>
            <p className="text-slate-400 text-sm">
              This usually takes just a few seconds.
            </p>
            <div className="flex justify-center">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <Card className="w-full max-w-lg bg-slate-800/95 border-slate-700">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4">
              <CheckCircle className="h-16 w-16 text-green-400" />
            </div>
            <CardTitle className="text-white text-2xl">Payment Successful!</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center">
              <p className="text-lg text-green-400 font-semibold mb-2">
                Welcome to Storm Oracle Premium! 🌪️
              </p>
              <p className="text-slate-300">
                Your subscription has been activated and you now have access to all premium features.
              </p>
            </div>

            {paymentDetails && (
              <div className="bg-slate-700/50 rounded-lg p-4 space-y-2">
                <h3 className="text-white font-semibold mb-3">Payment Details</h3>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Amount:</span>
                  <span className="text-white">
                    ${(paymentDetails.amount_total / 100).toFixed(2)} {paymentDetails.currency.toUpperCase()}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Session ID:</span>
                  <span className="text-white font-mono text-xs">{paymentDetails.session_id.slice(-8)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Status:</span>
                  <span className="text-green-400 font-semibold">{paymentDetails.payment_status}</span>
                </div>
              </div>
            )}

            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
              <h3 className="text-blue-400 font-semibold mb-2">What's Next?</h3>
              <ul className="text-sm text-slate-300 space-y-1">
                <li>• Access real-time tornado tracking</li>
                <li>• View advanced storm predictions</li>
                <li>• Set up custom alert zones</li>
                <li>• Explore historical radar data</li>
                <li>• Use the full-screen radar mode</li>
              </ul>
            </div>

            <div className="flex space-x-3">
              <Button 
                className="flex-1 bg-blue-600 hover:bg-blue-700"
                onClick={handleContinue}
              >
                Start Using Premium
              </Button>
              <Button 
                variant="outline"
                className="flex-1 border-slate-600 text-white hover:bg-slate-700"
                onClick={handleViewAccount}
              >
                View Account
              </Button>
            </div>

            <p className="text-center text-xs text-slate-500">
              You will receive a confirmation email shortly with your receipt and subscription details.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-800/95 border-slate-700">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            <AlertCircle className="h-12 w-12 text-red-400" />
          </div>
          <CardTitle className="text-white">Payment Verification Failed</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-slate-300">
            We couldn't verify your payment status. This might be due to:
          </p>
          <ul className="text-left text-slate-400 text-sm space-y-1">
            <li>• Payment session expired</li>
            <li>• Network connectivity issues</li>
            <li>• Payment was cancelled</li>
          </ul>
          <div className="space-y-2">
            <Button 
              className="w-full bg-blue-600 hover:bg-blue-700"
              onClick={() => window.location.reload()}
            >
              Try Again
            </Button>
            <Button 
              variant="outline"
              className="w-full border-slate-600 text-white hover:bg-slate-700"
              onClick={() => window.location.href = '/pricing'}
            >
              Back to Pricing
            </Button>
          </div>
          <p className="text-xs text-slate-500">
            If you continue to have issues, please contact support at support@stormoracle.com
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentSuccess;