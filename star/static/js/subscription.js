(() => {
    const page = document.querySelector('.plans-page');
    if (!page) return;

    const message = page.querySelector('[data-payment-message]');
    const csrfToken = page.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    const showMessage = (text, isError = false) => {
        message.textContent = text;
        message.classList.toggle('is-error', isError);
    };

    const post = (url, body, json = false) => fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, ...(json ? { 'Content-Type': 'application/json' } : {}) },
        body: json ? JSON.stringify(body) : new URLSearchParams(body),
        credentials: 'same-origin'
    }).then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Request failed');
        return data;
    });

    page.querySelectorAll('[data-plan-id]').forEach(button => {
        button.addEventListener('click', async () => {
            button.disabled = true;
            button.textContent = 'Starting payment...';
            showMessage('Connecting to secure checkout...');
            try {
                const order = await post(page.dataset.createUrl, { plan_id: button.dataset.planId });
                if (!window.Razorpay) throw new Error('Secure checkout is unavailable right now.');
                const checkout = new Razorpay({
                    key: order.key,
                    amount: order.amount,
                    currency: order.currency,
                    name: 'FitZone Gym',
                    description: order.plan,
                    order_id: order.order_id,
                    prefill: { name: order.user_name, email: order.user_email },
                    handler: async response => {
                        showMessage('Verifying your payment...');
                        try {
                            const result = await post(page.dataset.verifyUrl, response, true);
                            showMessage('Payment successful! Your gym subscription has been activated.');
                            button.textContent = 'Subscription active';
                            setTimeout(() => window.location.reload(), 900);
                        } catch (error) {
                            showMessage(error.message, true);
                            button.disabled = false;
                            button.textContent = 'Try again';
                        }
                    },
                    modal: { ondismiss: () => {
                        post(page.dataset.failedUrl, { razorpay_order_id: order.order_id, status: 'cancelled', error_description: 'Payment window closed' }).catch(() => {});
                        showMessage('Payment was cancelled. You can try again.', true);
                        button.disabled = false;
                        button.textContent = 'Try again';
                    } }
                });
                checkout.on('payment.failed', failure => {
                    post(page.dataset.failedUrl, { razorpay_order_id: order.order_id, error_description: failure.error?.description || 'Payment failed' }).catch(() => {});
                    showMessage('Payment failed. Please try again.', true);
                    button.disabled = false;
                    button.textContent = 'Try again';
                });
                checkout.open();
            } catch (error) {
                showMessage(error.message, true);
                button.disabled = false;
                button.textContent = 'Try again';
            }
        });
    });
})();
