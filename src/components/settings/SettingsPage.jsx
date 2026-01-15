import React from 'react';
import { useAuthStore } from '../../store/authStore';
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Users,
  Key,
  Mail,
} from 'lucide-react';
import * as Switch from '@radix-ui/react-switch';

function SettingSection({ title, description, icon: Icon, children }) {
  return (
    <div className="card p-6">
      <div className="flex items-start gap-4 mb-6">
        <div className="p-2 rounded-lg bg-neutral-100">
          <Icon className="w-5 h-5 text-neutral-600" />
        </div>
        <div>
          <h3 className="font-semibold text-neutral-900">{title}</h3>
          <p className="text-sm text-neutral-500">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-neutral-900">Settings</h2>
        <p className="text-neutral-500">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <SettingSection
        title="Profile"
        description="Update your personal information"
        icon={User}
      >
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-2xl font-semibold text-primary-700">
                {user?.name?.charAt(0) || 'U'}
              </span>
            </div>
            <button className="btn btn-secondary">Change photo</button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Full name
              </label>
              <input
                type="text"
                defaultValue={user?.name || 'Demo User'}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Email
              </label>
              <input
                type="email"
                defaultValue={user?.email || 'demo@vibber.ai'}
                className="input"
                disabled
              />
            </div>
          </div>

          <button className="btn btn-primary">Save changes</button>
        </div>
      </SettingSection>

      {/* Notifications */}
      <SettingSection
        title="Notifications"
        description="Configure how you receive alerts"
        icon={Bell}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-neutral-900">Escalation alerts</p>
              <p className="text-sm text-neutral-500">
                Get notified when your agent needs help
              </p>
            </div>
            <Switch.Root
              defaultChecked
              className="w-11 h-6 bg-neutral-200 rounded-full relative data-[state=checked]:bg-primary-500 outline-none cursor-pointer"
            >
              <Switch.Thumb className="block w-5 h-5 bg-white rounded-full shadow-md transition-transform translate-x-0.5 data-[state=checked]:translate-x-[22px]" />
            </Switch.Root>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-neutral-900">Daily digest</p>
              <p className="text-sm text-neutral-500">
                Summary of your agent's daily activity
              </p>
            </div>
            <Switch.Root
              defaultChecked
              className="w-11 h-6 bg-neutral-200 rounded-full relative data-[state=checked]:bg-primary-500 outline-none cursor-pointer"
            >
              <Switch.Thumb className="block w-5 h-5 bg-white rounded-full shadow-md transition-transform translate-x-0.5 data-[state=checked]:translate-x-[22px]" />
            </Switch.Root>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-neutral-900">Weekly reports</p>
              <p className="text-sm text-neutral-500">
                Performance analytics sent to your email
              </p>
            </div>
            <Switch.Root
              className="w-11 h-6 bg-neutral-200 rounded-full relative data-[state=checked]:bg-primary-500 outline-none cursor-pointer"
            >
              <Switch.Thumb className="block w-5 h-5 bg-white rounded-full shadow-md transition-transform translate-x-0.5 data-[state=checked]:translate-x-[22px]" />
            </Switch.Root>
          </div>
        </div>
      </SettingSection>

      {/* Security */}
      <SettingSection
        title="Security"
        description="Protect your account"
        icon={Shield}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-neutral-900">Two-factor authentication</p>
              <p className="text-sm text-neutral-500">
                Add an extra layer of security
              </p>
            </div>
            <button className="btn btn-secondary">Enable</button>
          </div>

          <div className="pt-4 border-t border-neutral-200">
            <button className="btn btn-ghost text-neutral-600">
              <Key className="w-4 h-4 mr-2" />
              Change password
            </button>
          </div>
        </div>
      </SettingSection>

      {/* Billing */}
      <SettingSection
        title="Billing"
        description="Manage your subscription"
        icon={CreditCard}
      >
        <div className="space-y-4">
          <div className="p-4 bg-primary-50 rounded-lg border border-primary-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-primary-900">Pro Plan</p>
                <p className="text-sm text-primary-700">$20/user/month</p>
              </div>
              <span className="badge badge-success">Active</span>
            </div>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-neutral-900">Current users</p>
              <p className="text-sm text-neutral-500">1 of 5 seats used</p>
            </div>
            <button className="btn btn-secondary">Manage seats</button>
          </div>

          <button className="btn btn-ghost text-neutral-600">
            View billing history
          </button>
        </div>
      </SettingSection>

      {/* Team */}
      <SettingSection
        title="Team"
        description="Manage team members"
        icon={Users}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                <span className="font-medium text-primary-700">
                  {user?.name?.charAt(0) || 'U'}
                </span>
              </div>
              <div>
                <p className="font-medium text-neutral-900">{user?.name || 'Demo User'}</p>
                <p className="text-sm text-neutral-500">Admin</p>
              </div>
            </div>
            <span className="badge badge-neutral">You</span>
          </div>

          <button className="btn btn-primary w-full">
            <Mail className="w-4 h-4 mr-2" />
            Invite team member
          </button>
        </div>
      </SettingSection>

      {/* Danger zone */}
      <div className="card p-6 border-error-200">
        <h3 className="font-semibold text-error-600 mb-2">Danger Zone</h3>
        <p className="text-sm text-neutral-500 mb-4">
          Irreversible and destructive actions
        </p>
        <button className="btn btn-danger">Delete account</button>
      </div>
    </div>
  );
}
