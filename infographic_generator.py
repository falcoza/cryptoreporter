from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from config import *

def generate_infographic(data):
    try:
        # Load fonts
        georgia = ImageFont.truetype(FONT_PATHS['georgia'], 18)
        georgia_bold = ImageFont.truetype(FONT_PATHS['georgia_bold'], 20)
        footer_font = ImageFont.truetype(FONT_PATHS['georgia'], 16)

        # Only Crypto metrics mapping
        crypto_map = {
            "BTCZAR": "Bitcoin ZAR",
            "ETHZAR": "Ethereum ZAR",
            "BNBZAR": "Binance Coin ZAR",
            "XRPZAR": "Ripple ZAR",
            "ADAZAR": "Cardano ZAR",
            "SOLZAR": "Solana ZAR",
            "DOGEZAR": "Dogecoin ZAR",
            "DOTZAR": "Polkadot ZAR",
            "TRXZAR": "Tron ZAR",
            "LTCZAR": "Litecoin ZAR",
        }
        metrics = []
        for key, name in crypto_map.items():
            if key in data:
                metrics.append((name, data[key]))

        # Dynamic canvas height for crypto-only
        row_height = 34
        header_height = 90  # header + table headers
        footer_space = 50
        total_height = header_height + len(metrics) * row_height + footer_space

        # Create canvas
        img = Image.new("RGB", (520, total_height), THEME['background'])
        draw = ImageDraw.Draw(img)

        # Header
        header_text = f"Crypto Market Report {data['timestamp']}"
        header_width = georgia_bold.getlength(header_text)
        draw.text(
            ((520 - header_width) // 2, 15),
            header_text,
            font=georgia_bold,
            fill=THEME['text']
        )

        # Table headers
        y_position = 60
        x_position = 25
        for col_name, col_width in REPORT_COLUMNS:
            draw.rectangle(
                [(x_position, y_position), (x_position + col_width, y_position + 30)],
                fill=THEME['header']
            )
            text_width = georgia_bold.getlength(col_name)
            draw.text(
                (x_position + (col_width - text_width) // 2, y_position + 5),
                col_name,
                font=georgia_bold,
                fill="white"
            )
            x_position += col_width

        # Data rows for crypto
        y_position = 90
        for idx, (metric_name, values) in enumerate(metrics):
            x_position = 25
            bg_color = "#F5F5F5" if idx % 2 == 0 else THEME['background']
            draw.rectangle(
                [(25, y_position), (520 - 25, y_position + row_height)],
                fill=bg_color
            )
            # Metric name
            draw.text((x_position + 5, y_position + 5), metric_name, font=georgia, fill=THEME['text'])
            x_position += REPORT_COLUMNS[0][1]

            # Today's value
            today_val = values.get("Today")
            today_text = f"{today_val:,.0f}" if today_val and today_val > 1000 else f"{today_val:,.2f}"
            draw.text((x_position + 5, y_position + 5), today_text, font=georgia, fill=THEME['text'])
            x_position += REPORT_COLUMNS[1][1]

            # Percentage columns: Change, Monthly, YTD
            for i, period in enumerate(["Change", "Monthly", "YTD"], start=2):
                value = values.get(period)
                color = THEME['positive'] if value is not None and value >= 0 else THEME['negative']
                text = f"{value:+.1f}%" if value is not None else ""
                col_width = REPORT_COLUMNS[i][1]
                text_width = georgia.getlength(text)
                draw.text(
                    (x_position + (col_width - text_width) // 2, y_position + 5),
                    text,
                    font=georgia,
                    fill=color
                )
                x_position += col_width

            y_position += row_height

        # Footer
        footer_text = "Data: CoinGecko"
        footer_width = footer_font.getlength(footer_text)
        draw.text(
            (520 - footer_width - 15, total_height - 25),
            footer_text,
            font=footer_font,
            fill="#666666"
        )

        # Save image
        filename = f"Crypto_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
        img.save(filename)
        return filename

    except Exception as e:
        raise RuntimeError(f"Infographic generation failed: {str(e)}")
