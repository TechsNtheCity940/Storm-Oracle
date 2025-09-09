import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Check, Zap, Crown, Building2 } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

const PaymentPlan = ({ user, onSubscriptionUpdate }) => {
  const [loading, setLoading] = useState(false);
  const [packages, setPackages] = useState({});
  const [trialStatus, setTrialStatus] = useState(null);
  const [subscriptionFeatures, setSubscriptionFeatures] = useState(null);

  useEffect(() => {
    loadPackages();
    if (user) {
      loadTrialStatus();
      loadSubscriptionFeatures();
    }
  }, [user]);

  const loadPackages = async () => {
    try {
      const response = await axios.get(`${API}/api/payments/packages`);
      setPackages(response.data.packages);
    } catch (error) {
      console.error('Error loading payment packages:', error);
    }
  };

  const loadTrialStatus = async () => {
    try {
      const token = localStorage.getItem('storm_oracle_token');
      if (!token) return;

      const response = await axios.get(`${API}/api/auth/trial-status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setTrialStatus(response.data);
    } catch (error) {
      console.error('Error loading trial status:', error);
    }
  };

  const loadSubscriptionFeatures = async () => {
    try {
      const token = localStorage.getItem('storm_oracle_token');
      if (!token) return;

      const response = await axios.get(`${API}/api/subscription/features`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setSubscriptionFeatures(response.data);
    } catch (error) {
      console.error('Error loading subscription features:', error);
    }
  };

  const handleSubscribe = async (packageId) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('storm_oracle_token');
      if (!token) {
        alert('Please login to subscribe');
        return;
      }

      const response = await axios.post(
        `${API}/api/payments/checkout/session`,
        {
          package_id: packageId,
          origin_url: window.location.origin,
          metadata: {
            source: 'storm_oracle_web',
            user_tier_upgrade: packageId
          }
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      // Redirect to Stripe Checkout
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Payment error:', error);
      alert('Payment setup failed. Please try again.');
    }
    setLoading(false);
  };

  const planFeatures = {
    free: [
      '🎯 Live 2D radar data access',
      '📍 Manual/nearest radar selection',
      '🗺️ All map controls (zoom, pan, fullscreen)',
      '🎬 Radar animation (max 100 frames)',
      '⚡ Up to 5x animation speed',
      '🤖 Location-based AI predictions',
      '👁️ Visual prediction data access',
      '139 NEXRAD station access',
      'Auto-looping radar on app load',
      'Community support'
    ],
    premium: [
      '✨ Everything in Enhanced Free tier',
      '🌪️ Advanced ML tornado predictions',
      '📊 2D & 3D radar data types',
      '♾️ Unlimited animation frames & speed',
      '🎯 Real-time storm tracking',
      '🚨 Enhanced AI alert system',
      '💬 AI chatbot for weather queries',
      '📈 Detailed prediction analytics',
      '🎛️ Advanced radar controls',
      '⚡ Priority support',
      '📤 Data export capabilities',
      '📋 Custom alert zones'
    ],
    enterprise: [
      'Everything in Premium',
      'Unlimited API access',
      'White-label solutions', 
      'Custom integrations',
      '24/7 priority support',
      'Advanced analytics',
      'Multi-user management',
      'Custom ML model training'
    ]
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-4">
          🌪️ Storm Oracle Pricing
        </h1>
        <p className="text-xl text-slate-300">
          Professional weather intelligence for everyone
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8">
        {/* Free Tier */}
        <Card className="bg-slate-800/95 border-slate-700 relative">
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Zap className="h-6 w-6 text-blue-400" />
              <CardTitle className="text-white">Free Tier</CardTitle>
            </div>
            <div className="text-3xl font-bold text-white">
              $0<span className="text-lg text-slate-400">/month</span>
            </div>
            <CardDescription className="text-slate-300">
              Perfect for weather enthusiasts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {planFeatures.free.map((feature, index) => (
                <li key={index} className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-green-400" />
                  <span className="text-slate-300 text-sm">{feature}</span>
                </li>
              ))}
            </ul>
            <Button 
              variant="outline" 
              className="w-full border-slate-600 text-white hover:bg-slate-700"
              disabled
            >
              Current Plan
            </Button>
          </CardContent>
        </Card>

        {/* Premium Monthly */}
        <Card className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border-purple-500 relative">
          <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-purple-600">
            Most Popular
          </Badge>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Crown className="h-6 w-6 text-purple-400" />
              <CardTitle className="text-white">Premium Monthly</CardTitle>
            </div>
            <div className="text-3xl font-bold text-white">
              $19.99<span className="text-lg text-slate-400">/month</span>
            </div>
            <CardDescription className="text-slate-300">
              Full access to professional features
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {planFeatures.premium.slice(0, 8).map((feature, index) => (
                <li key={index} className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-green-400" />
                  <span className="text-slate-300 text-sm">{feature}</span>
                </li>
              ))}
              <li className="text-slate-500 text-sm">+ more premium features</li>
            </ul>
            <Button 
              className="w-full bg-purple-600 hover:bg-purple-700"
              onClick={() => handleSubscribe('premium_monthly')}
              disabled={loading || user?.subscription_type === 'premium'}
            >
              {loading ? 'Processing...' : 'Subscribe Monthly'}
            </Button>
          </CardContent>
        </Card>

        {/* Premium Annual */}
        <Card className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border-green-500 relative">
          <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-green-600">
            Save 17%
          </Badge>
          <CardHeader>
            <div className="flex items-center space-x-2">
              <Crown className="h-6 w-6 text-green-400" />
              <CardTitle className="text-white">Premium Annual</CardTitle>
            </div>
            <div className="text-3xl font-bold text-white">
              $199.99<span className="text-lg text-slate-400">/year</span>
            </div>
            <div className="text-sm text-green-400 font-semibold">
              Save $39.89 vs monthly
            </div>
            <CardDescription className="text-slate-300">
              Best value for serious users
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {planFeatures.premium.slice(0, 8).map((feature, index) => (
                <li key={index} className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-green-400" />
                  <span className="text-slate-300 text-sm">{feature}</span>
                </li>
              ))}
              <li className="flex items-center space-x-2">
                <Check className="h-4 w-4 text-green-400" />
                <span className="text-green-400 text-sm font-semibold">Extended API access (5000 calls/month)</span>
              </li>
            </ul>
            <Button 
              className="w-full bg-green-600 hover:bg-green-700"
              onClick={() => handleSubscribe('premium_annual')}
              disabled={loading || user?.subscription_type === 'premium'}
            >
              {loading ? 'Processing...' : 'Subscribe Annually'}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Enterprise Section */}
      <Card className="mt-8 bg-gradient-to-r from-yellow-900/20 to-orange-900/20 border-yellow-500">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Building2 className="h-6 w-6 text-yellow-400" />
              <CardTitle className="text-white">Enterprise</CardTitle>
              <Badge className="bg-yellow-600">Contact Sales</Badge>
            </div>
            <div className="text-2xl font-bold text-white">
              Custom Pricing
            </div>
          </div>
          <CardDescription className="text-slate-300">
            Enterprise-grade weather intelligence platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <ul className="space-y-2">
              {planFeatures.enterprise.slice(0, 4).map((feature, index) => (
                <li key={index} className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-green-400" />
                  <span className="text-slate-300">{feature}</span>
                </li>
              ))}
            </ul>
            <ul className="space-y-2">
              {planFeatures.enterprise.slice(4).map((feature, index) => (
                <li key={index} className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-green-400" />
                  <span className="text-slate-300">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-6">
            <Button 
              variant="outline" 
              className="border-yellow-600 text-yellow-400 hover:bg-yellow-600 hover:text-white"
              onClick={() => window.open('mailto:enterprise@stormoracle.com?subject=Enterprise%20Inquiry')}
            >
              Contact Enterprise Sales
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Current User Status */}
      {user && (
        <Card className="mt-6 bg-slate-800/95 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center space-x-2">
              <span>Your Current Plan</span>
              <Badge variant={user.subscription_type === 'admin' ? 'default' : 'secondary'}>
                {user.subscription_type === 'admin' ? 'Admin' : user.subscription_type?.toUpperCase() || 'FREE'}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-300">
                  Account: {user.full_name} ({user.email})
                </p>
                <p className="text-slate-400 text-sm">
                  {user.subscription_type === 'admin' ? 'Full admin access to all features' : 
                   user.subscription_type === 'premium' ? 'Premium subscription active' :
                   'Free tier - upgrade for more features'}
                </p>
              </div>
              {user.subscription_type === 'free' && (
                <Button 
                  className="bg-purple-600 hover:bg-purple-700"
                  onClick={() => handleSubscribe('premium_monthly')}
                >
                  Upgrade Now
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PaymentPlan;