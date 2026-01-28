<?php

namespace App\Providers;

use Illuminate\Auth\Notifications\VerifyEmail;
use Illuminate\Foundation\Support\Providers\AuthServiceProvider as ServiceProvider;
use Illuminate\Notifications\Messages\MailMessage;

class AuthServiceProvider extends ServiceProvider
{
    /**
     * The model to policy mappings for the application.
     *
     * @var array<class-string, class-string>
     */
    protected $policies = [];

    public function boot(): void
    {
        VerifyEmail::toMailUsing(function ($notifiable, $url) {
            $frontendUrl = config('app.frontend_url') . '/verify-email?url=' . urlencode($url);

            return (new MailMessage)
                ->subject('Verify Email Address')
                ->line('Please click the button below to verify your email address.')
                ->action('Verify Email Address', $frontendUrl)
                ->line('If you did not create an account, no further action is required.');
        });
    }
}
