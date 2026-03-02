/** @odoo-module **/

/**
 * Converts a number to Indian currency words (Rupees and Paise)
 */
export function amountToWords(amount) {
    const ones = [
        '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
        'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
        'Seventeen', 'Eighteen', 'Nineteen'
    ];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

    function convertHundreds(n) {
        if (n === 0) return '';
        if (n < 20) return ones[n];
        if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? ' ' + ones[n % 10] : '');
        return ones[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + convertHundreds(n % 100) : '');
    }

    function convertIndian(n) {
        if (n === 0) return 'Zero';
        let result = '';
        const crore = Math.floor(n / 10000000);
        n %= 10000000;
        const lakh = Math.floor(n / 100000);
        n %= 100000;
        const thousand = Math.floor(n / 1000);
        n %= 1000;

        if (crore) result += convertHundreds(crore) + ' Crore ';
        if (lakh) result += convertHundreds(lakh) + ' Lakh ';
        if (thousand) result += convertHundreds(thousand) + ' Thousand ';
        if (n) result += convertHundreds(n);
        return result.trim();
    }

    if (isNaN(amount) || amount === undefined) return '';
    const rounded = Math.round(amount * 100);
    const rupees = Math.floor(rounded / 100);
    const paise = rounded % 100;

    let words = 'Rupees ' + convertIndian(rupees);
    if (paise > 0) {
        words += ' and ' + convertIndian(paise) + ' Paise';
    }
    return words + ' Only';
}