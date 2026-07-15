import pandas as pd


def purchase_data():

    data = {

        "PO":[
            "PO001",
            "PO002",
            "PO003",
            "PO004"
        ],

        "Supplier":[
            "ABC Steel",
            "XYZ Traders",
            "Fast Supply",
            "Metro Parts"
        ],

        "Ordered":[
            1000,
            500,
            800,
            300
        ],

        "Received":[
            700,
            500,
            200,
            300
        ]

    }

    df=pd.DataFrame(data)

    df["Pending"] = (
        df["Ordered"]
        -
        df["Received"]
    )

    return df



def stock_data():

    return pd.DataFrame({

        "Item":[
            "Bearing",
            "Bolt",
            "Oil"
        ],

        "Stock":[
            120,
            500,
            80
        ],

        "Status":[
            "OK",
            "High",
            "Low"
        ]

    })