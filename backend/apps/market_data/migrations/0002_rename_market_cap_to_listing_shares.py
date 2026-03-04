from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("market_data", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stocklisting",
            old_name="market_cap",
            new_name="listing_shares",
        ),
    ]
